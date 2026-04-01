#!/bin/bash
# =============================================================================
# Nova – Raspberry Pi 4B+ Setup-Skript
# Betriebssystem: Raspberry Pi OS Lite 64-bit (bookworm) – empfohlen
#
# Was dieses Skript macht:
#   1. Systempakete aktualisieren
#   2. Python 3.11+ + pip sicherstellen
#   3. Projektabhängigkeiten installieren
#   4. Ollama installieren + Modell herunterladen
#   5. Faster-Whisper für lokales STT installieren
#   6. Datenpfade anlegen (außerhalb Git-Repo)
#   7. config.json aus Vorlage erstellen (falls nicht vorhanden)
#   8. systemd-Service für Autostart einrichten
#
# Verwendung:
#   chmod +x scripts/setup_pi.sh
#   ./scripts/setup_pi.sh
#
# Empfohlenes OS: https://www.raspberrypi.com/software/
#   → "Raspberry Pi OS Lite (64-bit)" auswählen
#   → SSH aktivieren, WLAN konfigurieren
# =============================================================================

set -e  # Bei Fehler abbrechen

NOVA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${HOME}/nova_data"
BACKUP_DIR="${HOME}/nova_backups"
VENV_DIR="${NOVA_DIR}/.venv"

echo "============================================="
echo "  Nova – Raspberry Pi Setup"
echo "  Installationsverzeichnis: ${NOVA_DIR}"
echo "  Datenpfad: ${DATA_DIR}"
echo "  Backup-Pfad: ${BACKUP_DIR}"
echo "============================================="
echo ""

# -------------------------------------------------------------------------
# 1. Systempakete
# -------------------------------------------------------------------------
echo "[1/8] Systempakete aktualisieren …"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    portaudio19-dev \
    libsndfile1 \
    ffmpeg \
    git \
    curl \
    sqlite3 \
    espeak-ng \
    libespeak-ng1

# -------------------------------------------------------------------------
# 2. Python Virtual Environment
# -------------------------------------------------------------------------
echo "[2/8] Python Virtual Environment anlegen …"
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip -q

# -------------------------------------------------------------------------
# 3. Nova-Abhängigkeiten
# -------------------------------------------------------------------------
echo "[3/8] Nova-Abhängigkeiten installieren …"
pip install -q cryptography

# TTS (pyttsx3 nutzt espeak-ng, das oben installiert wurde)
pip install -q pyttsx3

# STT (SpeechRecognition als Fallback)
pip install -q SpeechRecognition

# PyAudio für Mikrofon
pip install -q pyaudio || echo "  PyAudio-Warnung: ggf. manuell nachinstallieren"

# -------------------------------------------------------------------------
# 4. Faster-Whisper (lokales STT)
# -------------------------------------------------------------------------
echo "[4/8] Faster-Whisper installieren (lokales STT) …"
pip install -q faster-whisper
echo "  Whisper 'tiny'-Modell wird beim ersten Start automatisch geladen."
echo "  Für bessere Qualität: In config.json 'whisper_model': 'base' setzen."

# -------------------------------------------------------------------------
# 5. Ollama installieren
# -------------------------------------------------------------------------
echo "[5/8] Ollama installieren (lokales LLM) …"
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
    echo "  Ollama installiert."
else
    echo "  Ollama bereits installiert."
fi

# Ollama-Service starten
sudo systemctl enable ollama
sudo systemctl start ollama
sleep 3

# Modell herunterladen (llama3.2:1b = ~700 MB, läuft gut auf Pi 4B+ 4GB)
echo "  Lade LLM-Modell: llama3.2:1b (~700 MB, ca. 5-10 min je nach Verbindung) …"
ollama pull llama3.2:1b
echo "  Modell bereit."

# -------------------------------------------------------------------------
# 6. Datenpfade anlegen
# -------------------------------------------------------------------------
echo "[6/8] Datenpfade anlegen (außerhalb Git-Repo) …"
mkdir -p "${DATA_DIR}"
mkdir -p "${BACKUP_DIR}/daily"
echo "  Datenpfad: ${DATA_DIR}"
echo "  Backup-Pfad: ${BACKUP_DIR}"

# -------------------------------------------------------------------------
# 7. config.json anlegen
# -------------------------------------------------------------------------
echo "[7/8] Konfigurationsdatei anlegen …"
CONFIG_PATH="${NOVA_DIR}/config.json"
if [ ! -f "${CONFIG_PATH}" ]; then
    cat > "${CONFIG_PATH}" << CONFIGEOF
{
  "_comment": "Nova Konfiguration – Raspberry Pi",
  "db_path": "${DATA_DIR}/nova_data.db",
  "secret_key": "$(openssl rand -hex 32)",
  "stm_capacity": 20,
  "ollama": {
    "host": "http://localhost:11434",
    "model": "llama3.2:1b",
    "temperature": 0.7,
    "max_tokens": 512
  },
  "local_stt": {
    "whisper_model": "tiny",
    "device": "cpu",
    "compute_type": "int8",
    "language": "de"
  },
  "backup": {
    "enabled": true,
    "dir": "${BACKUP_DIR}",
    "max_backups": 30,
    "interval_sec": 3600
  },
  "voice": {
    "enabled": true,
    "language": "de-DE",
    "tts_rate": 160
  },
  "api": {
    "enabled": false
  }
}
CONFIGEOF
    echo "  Konfiguration erstellt: ${CONFIG_PATH}"
    # Secret key extrahieren und prominent anzeigen
    SECRET_KEY=$(python3 -c "import json; print(json.load(open('${CONFIG_PATH}'))['secret_key'])" 2>/dev/null || grep '"secret_key"' "${CONFIG_PATH}" | cut -d'"' -f4)
    echo ""
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║  ⚠️  WICHTIG: SECRET KEY SICHER AUFBEWAHREN!         ║"
    echo "  ║                                                      ║"
    echo "  ║  ${SECRET_KEY}"
    echo "  ║                                                      ║"
    echo "  ║  Ohne diesen Key können verschlüsselte Daten NICHT  ║"
    echo "  ║  wiederhergestellt werden!                           ║"
    echo "  ║  → In Passwortmanager speichern!                    ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo ""
else
    echo "  Konfiguration bereits vorhanden: ${CONFIG_PATH}"
fi

# -------------------------------------------------------------------------
# 8. systemd-Service installieren
# -------------------------------------------------------------------------
echo "[8/8] systemd-Service installieren …"
SERVICE_TEMPLATE="${NOVA_DIR}/scripts/nova.service"
SERVICE_DEST="/etc/systemd/system/nova.service"

if [ -f "${SERVICE_TEMPLATE}" ]; then
    # Platzhalter ersetzen (doppelte Anführungszeichen für Variable-Expansion)
    sudo bash -c "sed \
        -e \"s|__NOVA_DIR__|${NOVA_DIR}|g\" \
        -e \"s|__VENV_DIR__|${VENV_DIR}|g\" \
        -e \"s|__USER__|${USER}|g\" \
        \"${SERVICE_TEMPLATE}\" > \"${SERVICE_DEST}\""
    sudo systemctl daemon-reload
    sudo systemctl enable nova.service
    echo "  Nova-Service installiert und für Autostart aktiviert."
    echo "  Starten: sudo systemctl start nova"
    echo "  Status:  sudo systemctl status nova"
    echo "  Logs:    journalctl -u nova -f"
else
    echo "  WARNUNG: nova.service Template nicht gefunden!"
fi

# -------------------------------------------------------------------------
# Fertig
# -------------------------------------------------------------------------
echo ""
echo "============================================="
echo "  Setup abgeschlossen! 🎉"
echo ""
echo "  Nova starten:"
echo "    source ${VENV_DIR}/bin/activate"
echo "    python ${NOVA_DIR}/main.py --config ${CONFIG_PATH}"
echo ""
echo "  Oder als Service:"
echo "    sudo systemctl start nova"
echo ""
echo "  Backup-Verzeichnis: ${BACKUP_DIR}"
echo "  Datenbank: ${DATA_DIR}/nova_data.db"
echo "  Config: ${CONFIG_PATH}"
echo ""
echo "  WICHTIG: secret_key aus config.json sicher aufbewahren!"
echo "  Ohne ihn können verschlüsselte Daten NICHT wiederhergestellt werden."
echo "============================================="
