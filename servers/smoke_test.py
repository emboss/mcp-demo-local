"""Smoke-Test für beide MCP-Server - spricht MCP über HTTP, genau wie Claude Code oder VS Code.

Aufruf (im Ordner infra/):
    docker compose run --rm hr-secure python smoke_test.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from mcp import Client

SECURE_URL = os.environ.get("SECURE_URL", "http://hr-secure:8000/mcp")
NAIVE_URL = os.environ.get("NAIVE_URL", "http://hr-naive:8000/mcp")
AUDIT_FILE = Path(os.environ.get("AUDIT_FILE", "/audit/audit.jsonl"))
SECRET = urlparse(os.environ["DATABASE_URL"]).password  # darf in keiner Antwort auftauchen

FORBIDDEN_FIELDS = {"salary", "home_address", "performance_rating", "sick_days", "id", "manager_id"}
failures = 0


def check(condition: bool, label: str) -> None:
    global failures
    print(("  OK    " if condition else "  FEHLER ") + label)
    failures += not condition


async def call(client: Client, tool: str, **arguments):
    result = await client.call_tool(tool, arguments)
    text = "\n".join(block.text for block in result.content if hasattr(block, "text"))
    check(SECRET not in text + str(result.structured_content), f"{tool}{arguments}: kein Passwort in der Antwort")
    if result.is_error:  # Ablehnungen und Fehler kommen als MCP-Fehlerergebnis mit Text
        return text
    if result.structured_content is not None:  # Listen: {"result": [...]}
        return result.structured_content.get("result", result.structured_content)
    return json.loads(text)


def audit_lines() -> int:
    return len(AUDIT_FILE.read_text(encoding="utf-8").splitlines()) if AUDIT_FILE.exists() else 0


async def test_secure(mode: str) -> None:
    print(f"\n[hr-secure, Verbindungsmodus '{mode}']")
    before = audit_lines()
    async with Client(SECURE_URL, mode=mode) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        check(set(tools) == {"find_colleague", "org_chart", "list_teams", "salary_stats"}, f"Tools: {sorted(tools)}")
        check("name" in tools["find_colleague"].input_schema.get("properties", {}), "Parameter-Schema von find_colleague ist korrekt")

        people = await call(client, "find_colleague", name="Lena")
        check(isinstance(people, list) and people and people[0]["name"] == "Lena Hoffmann", "find_colleague findet Lena Hoffmann")
        check(all(not FORBIDDEN_FIELDS & set(person) for person in people), "find_colleague liefert keine sensiblen Felder")

        jonas = await call(client, "find_colleague", name="Jonas Weber")
        check("SYSTEMHINWEIS" in jonas[0]["bio"], "Prompt Injection steckt in der Bio von Jonas Weber")

        check(len(await call(client, "list_teams")) == 7, "list_teams liefert 7 Teams")
        check(len(await call(client, "org_chart", team="Recht")) == 2, "org_chart(Recht) liefert 2 Personen")

        all_seniors = await call(client, "salary_stats", role="Senior Software Engineer")
        berlin_seniors = await call(client, "salary_stats", role="Senior Software Engineer", office="Berlin")
        check(isinstance(all_seniors, dict) and all_seniors.get("durchschnittsgehalt_eur") == 87000,
              f"salary_stats(Senior SE) = {all_seniors}")
        if isinstance(berlin_seniors, dict):
            leaked = 6 * all_seniors["durchschnittsgehalt_eur"] - 5 * berlin_seniors["durchschnittsgehalt_eur"]
            print(f"  INFO  Differenz-Angriff (Übung) funktioniert noch: 6 x 87.000 - 5 x 85.000 = {leaked} EUR")
        else:
            print(f"  INFO  Differenz-Angriff wird abgewehrt (Übung gelöst): {berlin_seniors}")

        for arguments in ({"role": "Senior Software Engineer", "office": "Hamburg"}, {"role": "Justiziar"}, {"role": "Gibt es nicht"}):
            refused = await call(client, "salary_stats", **arguments)
            check("Abgelehnt:" in str(refused), f"salary_stats{arguments} wird abgelehnt: {refused}")
        refused = await call(client, "find_colleague", name="L")
        check("Abgelehnt:" in str(refused), f"Zu kurze Suche wird abgelehnt: {refused}")

    check(audit_lines() - before == 10, f"Audit-Log: {audit_lines() - before} neue Zeilen (erwartet 10, eine pro Tool-Aufruf)")


async def test_naive() -> None:
    print("\n[hr-naive - hier SOLLEN die Schwachstellen nachweisbar sein]")
    async with Client(NAIVE_URL, mode="legacy") as client:
        result = await client.call_tool("execute_sql", {"query": "SELECT salary FROM employees WHERE name = 'Lena Hoffmann'"})
        check("97000" in result.content[0].text, "Naiver Server verrät Einzelgehälter")
        result = await client.call_tool("execute_sql", {"query": "SELECT * FROM gibt_es_nicht"})
        check("postgresql://postgres:" in result.content[0].text, "Naiver Server verrät die Verbindungs-URL in Fehlermeldungen")


async def main() -> None:
    await test_secure("legacy")  # klassischer initialize-Handshake (ältere Clients)
    await test_secure("auto")    # neuere Protokoll-Aushandlung
    await test_naive()
    print("\nAlles in Ordnung." if failures == 0 else f"\n{failures} Prüfung(en) fehlgeschlagen.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
