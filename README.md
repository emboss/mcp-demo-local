# MCP als Sicherheitsschicht - HR-Verzeichnis-Demo

Ein lokaler MCP-Server für Seminare zur KI-gestützten Entwicklung. Er zeigt, wie ein MCP-Server
einem KI-Agenten **freigegebene Informationen** gibt, während **sensible Daten** (Gehälter, Adressen,
Leistungsbewertungen) und die **Datenbank-Zugangsdaten** für den Agenten unerreichbar bleiben.

Zum Vergleich läuft daneben ein **naiver Server**, der dem Agenten freies SQL als Datenbank-Superuser erlaubt.

```
 VS Code mit Claude Code, Codex oder GitHub Copilot (Ordner workspace/)
      │  HTTP, nur localhost
      ├──► hr-secure  :8000 ── Rolle hr_mcp (minimale Rechte) ──┐
      └──► hr-naive   :8001 ── Superuser postgres ──────────────┤
                                                                ▼
                                                  PostgreSQL (nur im Docker-Netz)
```

Die Firma „Kranich Software GmbH“ und alle Personen sind frei erfunden.

## Voraussetzungen

- **Docker Desktop** (Windows: mit WSL2-Backend; Virtualisierung muss im BIOS aktiv sein, die Installation braucht Admin-Rechte).
  Hinweis: In Unternehmen mit mehr als 250 Beschäftigten oder mehr als 10 Mio. USD Umsatz ist Docker Desktop
  lizenzpflichtig. Kostenlose Alternativen: Rancher Desktop, Podman Desktop.
- **VS Code** mit **Claude Code**, **Codex** oder **GitHub Copilot** (Agent-Modus).
- Git (oder das Repository als ZIP).

**Vorab-Check** (in PowerShell oder einem Terminal):

```powershell
docker run --rm hello-world
docker compose version
```

Beide Befehle müssen ohne Fehler durchlaufen.

## Einrichtung

```powershell
cd infra
Copy-Item .env.example .env      # macOS/Linux: cp .env.example .env
```

`infra/.env` öffnen und **beide Passwörter durch eigene Werte ersetzen** (nur Buchstaben, Ziffern, Bindestriche).
Dann starten:

```powershell
docker compose up -d --build
docker compose ps                # db, hr-secure und hr-naive müssen "running" sein
```

Optionaler Selbsttest (prüft beide Server über MCP):

```powershell
docker compose run --rm hr-secure python smoke_test.py
```

## KI-Client verbinden

In VS Code wird **immer der Ordner `workspace/` geöffnet** (*Datei → Ordner öffnen*), nicht der Hauptordner.
Die KI-Erweiterungen lesen ihre Konfiguration aus dem geöffneten Ordner:

| Datei in `workspace/` | Gelesen von | Inhalt |
|---|---|---|
| `.mcp.json` | Claude Code | die beiden MCP-Server (nur URLs, keine Passwörter) |
| `.claude/settings.json` | Claude Code | Sperrregeln: kein Zugriff auf `../infra/` und auf `docker` |
| `.codex/config.toml` | Codex | beide MCP-Server und das Leseprofil `workshop` für lokale Befehle |
| `.vscode/mcp.json` | GitHub Copilot | die beiden MCP-Server |

Warum der Hauptordner tabu ist, zeigt Akt 4 der Demo.

**Claude Code (Erweiterung)**

1. `workspace/` in VS Code öffnen.
2. Claude-Code-Panel öffnen: Spark-Symbol oben rechts in der Editor-Leiste (bei geöffneter Datei),
   Symbol in der Aktivitätsleiste oder „✻ Claude Code“ in der Statusleiste.
3. Fragt Claude Code, ob die Projekt-Server aus `.mcp.json` verwendet werden dürfen: bestätigen.
4. Im Chat `/mcp` eingeben: Beide Server (`hr-secure`, `hr-naive`) erscheinen und lassen sich einzeln
   aktivieren oder deaktivieren. **Änderungen gelten erst für neu gestartete Unterhaltungen.**

Alternativ im Terminal: `cd workspace` und `claude`. Es gelten dieselben Dateien.

**Codex (Erweiterung)**

1. `workspace/` in VS Code öffnen. Codex lädt die mitgelieferte `.codex/config.toml`, wenn der Ordner in Codex als vertrauenswürdig gilt (siehe unten).
2. Im Codex-Panel unter *Zahnrad → MCP servers* die beiden HR-Server prüfen. Für Akt 1 ist nur `hr-naive` aktiviert.
3. Ab Akt 2 und für die Challenges in `.codex/config.toml` bei `hr-naive` den Wert `enabled = false` und bei `hr-secure` den Wert `enabled = true` setzen. Über die Befehlspalette *Developer: Reload Window* ausführen und eine neue Codex-Unterhaltung starten.

#### Codex zeigt 0 MCP-Server

Codex verwaltet das Projektvertrauen separat vom Dialog *Workspace Trust* in VS Code.
Über *Codex Settings → Open config.toml* die persönliche Datei `~/.codex/config.toml` öffnen.
Dort den absoluten Pfad zum geöffneten Workshop-Ordner eintragen. Den Beispielpfad ersetzen.
Falls der Abschnitt schon existiert, den vorhandenen Wert ändern.

```toml
[projects.'/absoluter/pfad/zum/workspace']
trust_level = "trusted"
```

Das Agent-Fenster mit *Developer: Reload Window* neu laden und eine neue Codex-Unterhaltung öffnen.
Wer die Codex-CLI installiert hat, kann im Terminal im Ordner `workspace/` mit `codex mcp list`
die geladenen Server prüfen. [Codex-Konfiguration](https://developers.openai.com/codex/config-basic/)

**GitHub Copilot**

1. `workspace/` in VS Code öffnen.
2. `.vscode/mcp.json` öffnen und über den Link **Start** über jedem Server starten.
3. Copilot Chat im **Agent-Modus** öffnen; über das Werkzeug-Symbol siehst du die Tools der Server.

Für die Docker-Befehle unten das integrierte Terminal öffnen (*Terminal → Neues Terminal*). Es startet in
`workspace/`, also zuerst `cd ../infra`.

## Nützliche Befehle (im Ordner `infra/`)

| Zweck | Befehl |
|---|---|
| Audit-Log live verfolgen | `docker compose logs -f hr-secure` |
| Audit-Datei anzeigen | `docker compose exec hr-secure cat /audit/audit.jsonl` |
| Nach Code-Änderung neu starten | `docker compose up -d --build` |
| Alles stoppen | `docker compose down` |
| Alles zurücksetzen (Datenbank + Audit-Log) | `docker compose down -v` |

## Fehlerbehebung

- **Port 8000 oder 8001 belegt:** In `infra/.env` z. B. `HR_SECURE_PORT=8100` und `HR_NAIVE_PORT=8101` setzen,
  `docker compose up -d` ausführen und die URLs für die verwendete Erweiterung anpassen. In `workspace/` nutzt Claude Code dafür `.mcp.json`, Codex `.codex/config.toml` und GitHub Copilot `.vscode/mcp.json`.
- **„password authentication failed“ nach Änderung von `.env`:** Die Datenbank übernimmt Passwörter nur beim
  allerersten Start. Mit `docker compose down -v` zurücksetzen und neu starten.
- **Datenbank startet nicht, Fehler mit `\r` oder „bad interpreter“:** Die Skripte wurden mit Windows-Zeilenenden
  ausgecheckt. Das Repository mit Git klonen (die `.gitattributes` erzwingt LF) oder in VS Code für
  `infra/db/init/03-roles.sh` unten rechts von „CRLF“ auf „LF“ umstellen; danach `docker compose down -v`.

## Aufbau

```
infra/       Docker Compose, Datenbank-Schema, Testdaten, Datenbank-Rollen, .env (Geheimnisse!)
servers/     naive_server.py, secure_server.py, smoke_test.py, Dockerfile
workspace/   Arbeitsordner für den KI-Agenten mit Konfigurationen für Claude Code, Codex und GitHub Copilot
docs/        Leitfäden für Seminarleitende (Ablauf, Prompts, Lösungen)
```

Für die Seminarleitung gibt es je einen Leitfaden für [Claude Code](docs/instructor-guide-claude-code.md) und [Codex](docs/instructor-guide-codex.md).
