# Ein Image für beide MCP-Server (naiv und gehärtet); welcher startet, legt docker-compose.yml fest.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Nicht als root laufen. /audit gehört dem App-Benutzer, damit das Audit-Volume beschreibbar ist.
RUN useradd --create-home --uid 10001 app \
 && mkdir /audit && chown app:app /audit
USER app

COPY *.py ./
EXPOSE 8000
