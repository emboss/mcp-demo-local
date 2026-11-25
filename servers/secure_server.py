"""HR-Verzeichnis - GEHÄRTETER MCP-Server.

Der Agent bekommt freigegebene Informationen, aber nie die sensiblen Daten oder die Zugangsdaten:

  1. Nur zweckgebundene Tools, kein freies SQL.
  2. Nur öffentliche Felder (kein Gehalt, keine Adresse, keine Bewertung, keine Krankheitstage).
  3. Gehälter nur als Durchschnitt über Gruppen mit mindestens MIN_GROUP_SIZE Personen.
  4. Eingeschränkte Datenbank-Rolle hr_mcp (siehe infra/db/init/03-roles.sh) - Defense in Depth.
  5. Generische Fehlermeldungen an den Agenten, Details nur im Server-Log.
  6. Audit-Log: jeder Tool-Aufruf wird protokolliert.

Die Zugangsdaten stehen in der Umgebung dieses Containers. Kein Tool gibt sie je zurück.
"""

import functools
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings

DATABASE_URL = os.environ["DATABASE_URL"]  # Rolle hr_mcp, kommt aus docker-compose.yml
AUDIT_FILE = Path(os.environ.get("AUDIT_FILE", "/audit/audit.jsonl"))
MIN_GROUP_SIZE = 5  # k-Anonymität: kleinere Gruppen verraten Einzelpersonen
GENERIC_ERROR = "Interner Fehler. Details stehen im Server-Log."

log = logging.getLogger("hr-secure")
mcp = MCPServer(
    name="hr-secure",
    instructions=(
        "Mitarbeiterverzeichnis der Kranich Software GmbH. Liefert Kontaktdaten, Organigramme "
        "und anonymisierte Gehaltsstatistiken. Gehälter einzelner Personen, Adressen, "
        "Leistungsbewertungen und Krankheitstage sind nicht verfügbar."
    ),
)


# ---------------------------------------------------------------- Audit-Log

def audit(tool: str, arguments: dict, outcome: str, detail: str | int | None = None) -> None:
    """Schreibt eine JSON-Zeile pro Tool-Aufruf: ins Audit-Volume und auf stdout.

    Protokolliert wird, WER WAS gefragt hat und WIE es ausging - nie die Antwortdaten selbst.
    """
    entry = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": tool,
        "arguments": arguments,
        "outcome": outcome,  # ok | refused | error
        "detail": detail,
    }
    line = json.dumps(entry, ensure_ascii=False)
    print(f"AUDIT {line}", flush=True)
    with AUDIT_FILE.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


class Refused(Exception):
    """Die Anfrage ist zulässig formuliert, aber die Antwort würde zu viel preisgeben."""


def audited(tool_function):
    """Rahmen für jedes Tool: protokollieren, Ablehnungen erklären, Fehler verbergen."""

    @functools.wraps(tool_function)
    def wrapper(**arguments):
        name = tool_function.__name__
        try:
            result = tool_function(**arguments)
        except Refused as reason:
            audit(name, arguments, "refused", str(reason))
            raise ToolError(f"Abgelehnt: {reason}")
        except Exception:
            log.exception("Fehler in Tool %s", name)  # Details nur im Server-Log ...
            audit(name, arguments, "error")
            raise ToolError(GENERIC_ERROR)  # ... der Agent erfährt nichts über Interna
        audit(name, arguments, "ok", len(result) if isinstance(result, list) else None)
        return result

    return wrapper


def query(sql: str, params: tuple = ()) -> list[dict]:
    """Nur parametrisierte Abfragen - Eingaben des Agenten landen nie im SQL-Text."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------- Tools

@mcp.tool()
@audited
def find_colleague(name: str) -> list[dict]:
    """Sucht Kolleginnen und Kollegen nach (Teil-)Namen.

    Liefert nur öffentliche Profildaten: Name, Titel, Rolle, Team, Standort, E-Mail und
    Selbstbeschreibung (bio). Gehalt, Adresse, Bewertung und Krankheitstage sind nicht verfügbar.
    """
    if len(name.strip()) < 2:
        raise Refused("Bitte mindestens zwei Zeichen des Namens angeben.")
    return query(
        """SELECT name, title, role, team, office, email, bio
           FROM employees WHERE name ILIKE %s ORDER BY name LIMIT 10""",
        (f"%{name.strip()}%",),
    )


@mcp.tool()
@audited
def org_chart(team: str) -> list[dict]:
    """Zeigt die Mitglieder eines Teams mit Titel, Rolle und Vorgesetzten."""
    return query(
        """SELECT e.name, e.title, e.role, e.office, m.name AS manager
           FROM employees e LEFT JOIN employees m ON m.id = e.manager_id
           WHERE e.team = %s ORDER BY e.manager_id NULLS FIRST, e.name""",
        (team,),
    )


@mcp.tool()
@audited
def list_teams() -> list[dict]:
    """Listet alle Teams mit Anzahl der Mitglieder."""
    return query("SELECT team, count(id) AS members FROM employees GROUP BY team ORDER BY team")


@mcp.tool()
@audited
def salary_stats(role: str, office: str | None = None) -> dict:
    """Anonymisierte Gehaltsstatistik: Durchschnittsgehalt einer Rolle, optional je Standort.

    Antwortet nur für Gruppen mit mindestens 5 Personen, gerundet auf 1.000 Euro.
    Rollen-Bezeichnungen wie in org_chart (z. B. "Software Engineer").
    """
    [stats] = query(
        """SELECT count(*) AS n, avg(salary) AS average FROM salary_facts
           WHERE role = %s AND (%s::text IS NULL OR office = %s)""",
        (role, office, office),
    )
    if stats["n"] == 0:
        raise Refused(f"Keine Daten für Rolle '{role}'" + (f" in {office}." if office else "."))
    if stats["n"] < MIN_GROUP_SIZE:
        # Bewusst nicht die genaue Anzahl nennen - auch die wäre schon eine Information.
        raise Refused(f"Gruppe zu klein (weniger als {MIN_GROUP_SIZE} Personen) - Schutz vor Rückschlüssen auf Einzelne.")
    return {
        "rolle": role,
        "standort": office or "alle",
        "anzahl_personen": stats["n"],
        "durchschnittsgehalt_eur": int(round(stats["average"], -3)),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mcp.run(
        "streamable-http",
        host="0.0.0.0",  # im Container; nach außen nur über 127.0.0.1 erreichbar (docker-compose.yml)
        port=8000,
        stateless_http=True,
        # Schutz gegen DNS-Rebinding: nur Anfragen an localhost (bzw. den Compose-Dienstnamen) annehmen.
        transport_security=TransportSecuritySettings(
            allowed_hosts=["localhost:*", "127.0.0.1:*", "hr-secure:*"],
            allowed_origins=["http://localhost:*", "http://127.0.0.1:*"],
        ),
    )
