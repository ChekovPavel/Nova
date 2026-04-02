# ──────────────────────────────────────────────────────────
# Nova – Persönlicher KI-Assistent  ·  Dockerfile
# ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

LABEL maintainer="Nova Project"
LABEL description="Nova – Persönlicher KI-Assistent"

# Systemabhängigkeiten
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Nicht-Root-Benutzer
RUN useradd --create-home --shell /bin/bash nova
USER nova
WORKDIR /home/nova/app

# Python-Abhängigkeiten (gecacht, wenn sich requirements.txt nicht ändert)
COPY --chown=nova:nova requirements.txt .
RUN pip install --user --no-cache-dir cryptography>=41.0.0

# Anwendungscode
COPY --chown=nova:nova . .

# Datenverzeichnisse
RUN mkdir -p /home/nova/nova_data /home/nova/nova_backups

# Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV NOVA_DB_PATH=/home/nova/nova_data/nova_data.db

# Volumes für persistente Daten
VOLUME ["/home/nova/nova_data", "/home/nova/nova_backups"]

# Healthcheck
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD python -c "import nova; print('ok')" || exit 1

ENTRYPOINT ["python", "main.py"]
CMD ["--config", "config.json"]
