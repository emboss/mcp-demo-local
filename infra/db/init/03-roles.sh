#!/bin/bash
# Legt die eingeschränkte Datenbank-Rolle "hr_mcp" für den GEHÄRTETEN MCP-Server an.
# Defense in Depth: Selbst wenn der Server-Code einen Fehler hätte, kann diese Rolle
# Gehälter nie mit Namen verknüpfen und Adressen, Bewertungen und Krankheitstage gar nicht lesen.
#
# Das Passwort kommt aus der Umgebungsvariable HR_MCP_DB_PASSWORD (siehe infra/.env).
# Postgres führt dieses Skript nur beim allerersten Start aus (leeres Daten-Volume).
set -euo pipefail

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v hr_mcp_password="$HR_MCP_DB_PASSWORD" <<'EOSQL'

CREATE ROLE hr_mcp LOGIN PASSWORD :'hr_mcp_password';

GRANT CONNECT ON DATABASE hr TO hr_mcp;
GRANT USAGE ON SCHEMA public TO hr_mcp;

-- Nur die unkritischen Spalten (Spalten-Berechtigungen!) ...
GRANT SELECT (id, name, title, role, team, office, email, manager_id, bio)
    ON employees TO hr_mcp;

-- ... plus Gehälter ohne Namen und IDs.
GRANT SELECT ON salary_facts TO hr_mcp;

-- Kein Zugriff auf: salary (in employees), home_address, performance_rating, sick_days.
EOSQL
