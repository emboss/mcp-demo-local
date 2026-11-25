"""HR-Verzeichnis - NAIVER MCP-Server.

So bitte NICHT bauen! Dieser Server ist das abschreckende Beispiel für Akt 1:
  * ein einziges Tool, das beliebiges SQL ausführt,
  * Verbindung als Datenbank-Superuser,
  * "debug-freundliche" Fehlermeldungen.
"""

import json
import os

import psycopg
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

# Superuser-Zugang aus docker-compose.yml (infra/.env).
DATABASE_URL = os.environ["DATABASE_URL"]

mcp = MCPServer(
    name="hr-naive",
    instructions="Zugriff auf die HR-Datenbank der Kranich Software GmbH (PostgreSQL, Tabelle: employees).",
)


@mcp.tool()
def execute_sql(query: str) -> str:
    """Führt eine beliebige SQL-Abfrage auf der HR-Datenbank (PostgreSQL) aus.

    Tabelle employees: id, name, title, role, team, office, email, manager_id, bio,
    salary, home_address, performance_rating, sick_days.
    """
    try:
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            cursor = conn.execute(query)
            while cursor.nextset():  # mehrere Statements erlaubt: Ergebnis des letzten zurückgeben
                pass
            if cursor.description is None:
                return f"OK, {cursor.rowcount} Zeilen betroffen."
            columns = [column.name for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return json.dumps(rows, ensure_ascii=False, default=str, indent=1)
    except Exception as error:
        # "Hilfreich" fürs Debugging ... (Übung: Was ist hier das Problem?)
        return f"Abfrage über {DATABASE_URL} fehlgeschlagen: {error}"


if __name__ == "__main__":
    mcp.run(
        "streamable-http",
        host="0.0.0.0",  # im Container; nach außen nur über 127.0.0.1 erreichbar (docker-compose.yml)
        port=8000,
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=["localhost:*", "127.0.0.1:*", "hr-naive:*"],
            allowed_origins=["http://localhost:*", "http://127.0.0.1:*"],
        ),
    )
