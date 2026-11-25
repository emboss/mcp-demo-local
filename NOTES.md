The demo is built and tested on Linux with Docker. The smoke test passes: it talks MCP over HTTP to both servers and checks both the older and newer protocol handshake. I haven't run it from Claude Code, VS Code or Windows yet; details below.

To start it: `cd infra`, copy `.env.example` to `.env`, set both passwords, then `docker compose up -d --build`. Open Claude Code in `workspace/`. Everything for participants is in German, the code identifiers in English.

**What's in it**
- **Naive server** ([servers/naive_server.py](servers/naive_server.py), 57 lines): free SQL as the database superuser, with error messages that include the connection details.
- **Hardened server** ([servers/secure_server.py](servers/secure_server.py)): four narrow tools, a minimum group size of 5 for salaries, generic error messages, and an audit log.
- **Restricted database account:** the hardened server logs in as `hr_mcp`, which cannot read salaries with names or addresses at all, even if the server code had a bug.
- **Fictional data:** small groups so refusals visibly happen, an injection hidden in Jonas Weber's bio, and figures where the exercise attack comes out exactly (6 × 87,000 − 5 × 85,000 = 97,000, Lena Hoffmann's salary).
- **Instructor guide** ([docs/instructor-guide.md](docs/instructor-guide.md)): a timed script with the exact prompts, expected results and tested solutions.

**Tested and working**
- The `hr_mcp` account gets "permission denied" on salaries, addresses and `SELECT *`.
- With the database stopped, the hardened server says only "Interner Fehler", while the naive server's error shows the superuser password.
- The optional `COPY … FROM PROGRAM 'env'` trick through the naive server reveals the hardened server's password from inside the database container. It makes a strong moment in Act 1.
- An SQL-injection attempt in a tool parameter just returns "Keine Daten".
- The exercise attack works, and the solution in the guide blocks it.
- Each tool call writes exactly one line to the audit log.

**Changes from the plan**
- **SDK 2.x:** the current MCP Python SDK (2.3.0) renamed `FastMCP` to `MCPServer`, so the code uses the new name.
- **Refusals:** they come back as MCP error results. Returning them as normal results broke for tools that return lists.
- **Audit log location:** it lives in a Docker volume instead of `infra/audit/`, which avoids file-permission problems on Linux.
- **Ports are configurable** in `.env`, because your `dmv-api` devcontainer is already using port 8000. I tested on 18000/18001 and didn't touch it.
- **`requirements.txt`** instead of `pyproject.toml`, because it's simpler.

**Not yet verified, for your dry run**
- **The Act 4 deny rule.** The Claude Code docs don't describe relative `../` paths, so `Read(../infra/**)` may not work. I wanted to test it with a second headless Claude Code run, but the safety check blocked it because it needed all permission checks turned off. Quick test: in `workspace/`, ask Claude to read `../infra/.env.example`. The guide describes a fallback if it fails.
- **The demo in a real Claude Code or VS Code session.** The servers have only been called by the smoke test, not by an actual agent client.
- **Windows with Docker Desktop.**

**Two things to know**
- Per the docs, the Claude Code sandbox doesn't run on native Windows, only in WSL2. The guide presents Act 4 honestly as "guardrails, not a boundary".
- The stack is still running on ports 18000/18001. `infra/.env` contains my test passwords (excluded from git); replace them and reset with `docker compose down -v`. I didn't set up a git repository.