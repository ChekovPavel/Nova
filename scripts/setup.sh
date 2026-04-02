#!/bin/bash
# =============================================================================
# Nova – Universelles Setup-Skript (Linux / macOS / WSL)
#
# Was dieses Skript macht:
#   1. Python-Version prüfen (3.10+ erforderlich)
#   2. Virtual Environment anlegen und aktivieren
#   3. Alle Abhängigkeiten installieren (Basis + optionale)
#   4. config.json aus Vorlage erstellen (falls nicht vorhanden)
#   5. Secret Key automatisch generieren
#   6. Datenpfade anlegen
#   7. Ollama-Installation prüfen und ggf. installieren
#   8. LLM-Modell mit Benutzerauswahl herunterladen
#
# Verwendung:
#   chmod +x scripts/setup.sh
#   ./scripts/setup.sh
#
# Für Raspberry Pi: scripts/setup_pi.sh verwenden (enthält systemd-Service).
# =============================================================================

set -e  # Bei Fehler abbrechen

NOVA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${HOME}/nova_data"
BACKUP_DIR="${HOME}/nova_backups"
VENV_DIR="${NOVA_DIR}/.venv"
CONFIG_PATH="${NOVA_DIR}/config.json"

echo "============================================="
echo "  Nova – Setup"
echo "  Installationsverzeichnis: ${NOVA_DIR}"
echo "  Datenpfad:                ${DATA_DIR}"
echo "  Backup-Pfad:              ${BACKUP_DIR}"
echo "============================================="
echo ""

# -------------------------------------------------------------------------
# 1. Python-Version prüfen
# -------------------------------------------------------------------------
echo "[1/8] Python-Version prüfen …"
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VERSION=$("$cmd" -c "import sys; print(sys.version_info >= (3, 10))" 2>/dev/null)
        if [ "$VERSION" = "True" ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "  FEHLER: Python 3.10+ nicht gefunden."
    echo "  Bitte installieren: https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VERSION=$("$PYTHON_CMD" --version)
echo "  Gefunden: ${PYTHON_VERSION}"

# -------------------------------------------------------------------------
# 2. Virtual Environment anlegen
# -------------------------------------------------------------------------
echo "[2/8] Python Virtual Environment anlegen …"
if [ ! -d "${VENV_DIR}" ]; then
    "$PYTHON_CMD" -m venv "${VENV_DIR}"
    echo "  Neues Venv erstellt: ${VENV_DIR}"
else
    echo "  Vorhandenes Venv gefunden: ${VENV_DIR}"
fi

# Venv aktivieren
# shellcheck source=/dev/null
if [ -f "${VENV_DIR}/bin/activate" ]; then
    source "${VENV_DIR}/bin/activate"
elif [ -f "${VENV_DIR}/Scripts/activate" ]; then
    # Windows/WSL
    source "${VENV_DIR}/Scripts/activate"
fi
pip install --upgrade pip -q
echo "  Virtual Environment aktiviert."

# -------------------------------------------------------------------------
# 3. Abhängigkeiten installieren
# -------------------------------------------------------------------------
echo "[3/8] Nova-Abhängigkeiten installieren …"
pip install -q -r "${NOVA_DIR}/requirements.txt"
echo "  Basis-Abhängigkeiten installiert."

# Optionale Pakete
echo "  Optionale Pakete installieren …"
pip install -q cryptography pyttsx3 SpeechRecognition faster-whisper openai spacy \
    || echo "  Hinweis: Einige optionale Pakete konnten nicht installiert werden (nicht kritisch)."

# PyAudio (benötigt PortAudio – bei Fehler Hinweis ausgeben)
pip install -q PyAudio 2>/dev/null \
    || echo "  Hinweis: PyAudio nicht installiert. Für Mikrofon-Support: sudo apt install portaudio19-dev && pip install PyAudio"

# Deutsches spaCy-Modell laden
python -m spacy download de_core_news_sm -q 2>/dev/null \
    || echo "  Hinweis: spaCy-Modell de_core_news_sm nicht geladen (nicht kritisch)."

echo "  Alle Abhängigkeiten installiert."

# -------------------------------------------------------------------------
# 4. Datenpfade anlegen
# -------------------------------------------------------------------------
echo "[4/8] Datenpfade anlegen …"
mkdir -p "${DATA_DIR}"
mkdir -p "${BACKUP_DIR}"
echo "  Datenpfad:   ${DATA_DIR}"
echo "  Backup-Pfad: ${BACKUP_DIR}"

# -------------------------------------------------------------------------
# 5. config.json anlegen
# -------------------------------------------------------------------------
echo "[5/8] Konfigurationsdatei anlegen …"
if [ ! -f "${CONFIG_PATH}" ]; then
    SECRET_KEY=$(openssl rand -hex 32 2>/dev/null \
        || python -c "import secrets; print(secrets.token_hex(32))")

    # Modell-Standard abhängig von verfügbarem VRAM ermitteln
    DEFAULT_MODEL="llama3.1:8b"
    echo "  Empfohlenes Standardmodell: ${DEFAULT_MODEL}"

    cat > "${CONFIG_PATH}" << CONFIGEOF
{
  "_comment": "Nova Konfiguration",
  "db_path": "${DATA_DIR}/nova_data.db",
  "secret_key": "${SECRET_KEY}",
  "stm_capacity": 20,
  "ollama": {
    "host": "http://localhost:11434",
    "model": "${DEFAULT_MODEL}",
    "temperature": 0.7,
    "max_tokens": 512
  },
  "local_stt": {
    "whisper_model": "base",
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
    "tts_rate": 160,
    "tts_volume": 0.9
  },
  "api": {
    "enabled": false,
    "llm_endpoint": "https://api.openai.com/v1/chat/completions",
    "llm_api_key": "",
    "llm_model": "gpt-4o"
  }
}
CONFIGEOF
    echo "  Konfiguration erstellt: ${CONFIG_PATH}"
    echo ""
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║  ⚠️  WICHTIG: SECRET KEY SICHER AUFBEWAHREN!         ║"
    echo "  ║                                                      ║"
    echo "  ║  ${SECRET_KEY}  ║"
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
# 6. Ollama prüfen / installieren
# -------------------------------------------------------------------------
echo "[6/8] Ollama prüfen …"
if ! command -v ollama &>/dev/null; then
    echo "  Ollama nicht gefunden. Installation starten?"
    read -r -p "  Ollama jetzt installieren? [j/N] " INSTALL_OLLAMA
    if [[ "${INSTALL_OLLAMA}" =~ ^[jJyY]$ ]]; then
        echo "  Installiere Ollama …"
        curl -fsSL https://ollama.com/install.sh | sh
        echo "  Ollama installiert."
    else
        echo "  Übersprungen. Bitte Ollama manuell installieren: https://ollama.ai"
    fi
else
    echo "  Ollama bereits installiert: $(ollama --version 2>/dev/null || echo 'Version unbekannt')"
fi

# -------------------------------------------------------------------------
# 7. Ollama starten und Modell herunterladen
# -------------------------------------------------------------------------
echo "[7/8] Ollama-Modell herunterladen …"
if command -v ollama &>/dev/null; then
    # Ollama starten falls nicht laufend
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "  Starte Ollama im Hintergrund …"
        ollama serve &>/dev/null &
        sleep 3
    fi

    echo ""
    echo "  Welches Modell möchtest du verwenden?"
    echo ""
    echo "  ┌─────────────────────────────────────────────────────────────────────┐"
    echo "  │  [1] llama3.2:1b    ~700 MB  – Raspberry Pi / schwache Hardware     │"
    echo "  │  [2] llama3.2:3b    ~2 GB    – Raspberry Pi 4B+ 8 GB / alte PCs    │"
    echo "  │  [3] llama3.1:8b    ~4.7 GB  – Gaming-PC, 8 GB VRAM (empfohlen)    │"
    echo "  │  [4] qwen2.5:14b   ~8.2 GB  – Gaming-PC, 12 GB VRAM, gut für DE   │"
    echo "  │  [5] llama3.1:70b  ~40 GB   – High-End PC / mehrere GPUs           │"
    echo "  │  [6] Eigene Eingabe                                                 │"
    echo "  │  [0] Überspringen (Modell später mit 'ollama pull' laden)           │"
    echo "  └─────────────────────────────────────────────────────────────────────┘"
    echo ""
    read -r -p "  Auswahl [0-6]: " MODEL_CHOICE

    case "$MODEL_CHOICE" in
        1) PULL_MODEL="llama3.2:1b" ;;
        2) PULL_MODEL="llama3.2:3b" ;;
        3) PULL_MODEL="llama3.1:8b" ;;
        4) PULL_MODEL="qwen2.5:14b" ;;
        5) PULL_MODEL="llama3.1:70b" ;;
        6)
            read -r -p "  Modell-Name eingeben (z.B. mistral:7b): " PULL_MODEL
            ;;
        0|*)
            PULL_MODEL=""
            echo "  Übersprungen."
            ;;
    esac

    if [ -n "$PULL_MODEL" ]; then
        echo "  Lade Modell: ${PULL_MODEL} …"
        ollama pull "${PULL_MODEL}"
        echo "  Modell bereit: ${PULL_MODEL}"

        # Modell in config.json aktualisieren
        if command -v python &>/dev/null && [ -f "${CONFIG_PATH}" ]; then
            python - <<PYEOF
import json, sys
try:
    with open('${CONFIG_PATH}', 'r') as f:
        cfg = json.load(f)
    cfg.setdefault('ollama', {})['model'] = '${PULL_MODEL}'
    with open('${CONFIG_PATH}', 'w') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("  Modell in config.json aktualisiert.")
except Exception as e:
    print(f"  Hinweis: config.json konnte nicht aktualisiert werden: {e}")
PYEOF
        fi
    fi
else
    echo "  Ollama nicht verfügbar – Schritt übersprungen."
fi

# -------------------------------------------------------------------------
# 8. Abschlussmeldung
# -------------------------------------------------------------------------
echo ""
echo "[8/8] Setup abgeschlossen! 🎉"
echo ""
echo "============================================="
echo "  Nova starten:"
echo ""
echo "  source ${VENV_DIR}/bin/activate"
echo "  python ${NOVA_DIR}/main.py"
echo ""
echo "  GUI-Modus:"
echo "  python ${NOVA_DIR}/main.py --gui"
echo ""
echo "  Konfiguration:  ${CONFIG_PATH}"
echo "  Datenbank:      ${DATA_DIR}/nova_data.db"
echo "  Backup-Pfad:    ${BACKUP_DIR}"
echo ""
echo "  Für die vollständige Dokumentation:"
echo "  cat ${NOVA_DIR}/SETUP.md"
echo "============================================="
