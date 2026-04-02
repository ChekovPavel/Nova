# Nova – Vollständige Einrichtungsanleitung

Diese Anleitung führt dich Schritt für Schritt von der Installation bis zum
lauffähigen Nova-System – inklusive Empfehlung für das **beste aktuell
verfügbare KI-Modell** (Stand April 2026).

---

## Inhaltsverzeichnis

1. [Systemvoraussetzungen](#1-systemvoraussetzungen)
2. [Schritt-für-Schritt Installation](#2-schritt-für-schritt-installation)
3. [Beste KI-Modell-Empfehlung](#3-beste-ki-modell-empfehlung-stand-april-2026)
4. [Konfiguration](#4-konfiguration-schritt-für-schritt)
5. [Ollama vollständige Einrichtung](#5-ollama-vollständige-einrichtung)
6. [Nova starten und testen](#6-nova-starten-und-testen)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Systemvoraussetzungen

### Betriebssystem

| System | Unterstützt | Hinweis |
|--------|------------|---------|
| **Linux** (Ubuntu 22.04+, Debian 12+) | ✅ Empfohlen | Beste Performance und Kompatibilität |
| **macOS** (12 Monterey+) | ✅ Unterstützt | Apple Silicon (M1/M2/M3) nativ unterstützt |
| **Windows 10/11** | ✅ Unterstützt | Am besten über **WSL2** (Windows Subsystem for Linux) |
| **Raspberry Pi OS** (64-bit Bookworm) | ✅ Unterstützt | Eigenes Skript: `scripts/setup_pi.sh` |

### Python

- **Python 3.10 oder höher** erforderlich
- Empfohlen: Python 3.11 oder 3.12

```bash
python3 --version   # sollte 3.10+ anzeigen
```

### Hardware-Empfehlungen

#### 🍓 Raspberry Pi

| Modell | RAM | Empfohlenes LLM-Modell | Erwartete Geschwindigkeit |
|--------|-----|----------------------|--------------------------|
| Raspberry Pi 4B+ | 4 GB | `llama3.2:1b` | ~2–5 Tokens/s |
| Raspberry Pi 4B+ | 8 GB | `llama3.2:3b` oder `phi3.5:mini` | ~1–3 Tokens/s |
| Raspberry Pi 5 | 8 GB | `llama3.2:3b` | ~3–6 Tokens/s |

> **Hinweis:** Für den Raspberry Pi gibt es ein eigenes Setup-Skript mit
> systemd-Service-Integration: `scripts/setup_pi.sh`

#### 🖥️ Desktop / Laptop (ohne dedizierte GPU)

| RAM | Empfohlenes LLM-Modell | Hinweis |
|-----|----------------------|---------|
| 8 GB | `llama3.2:1b` | Langsam, aber funktional |
| 16 GB | `llama3.1:8b` (CPU) | Akzeptable Geschwindigkeit |
| 32 GB+ | `llama3.1:8b` oder `qwen2.5:14b` (CPU) | Gute Qualität |

#### 🎮 Gaming-PC / Workstation (NVIDIA GPU)

| VRAM | Empfohlenes LLM-Modell | Qualität |
|------|----------------------|---------|
| 6 GB VRAM | `llama3.2:3b` | Gut |
| 8 GB VRAM | `llama3.1:8b` ⭐ | **Sehr gut – Empfehlung** |
| 12 GB VRAM | `qwen2.5:14b` | Exzellent, sehr gut für Deutsch |
| 16 GB VRAM | `llama3.3:70b-q4` (quantisiert) | Hervorragend |
| 24 GB+ VRAM | `llama3.1:70b` | Maximale lokale Qualität |
| 2× 24 GB VRAM | `llama3.1:70b` (voll) | Maximale Qualität |

> **GPU-Tipp:** Nova nutzt Ollama für lokale Modelle. Mit einer NVIDIA-GPU
> läuft Ollama automatisch mit CUDA-Beschleunigung – die Tokens-pro-Sekunde
> Rate ist 5–20× schneller als auf der CPU.

---

## 2. Schritt-für-Schritt Installation

### Option A: Automatisches Setup-Skript (empfohlen)

```bash
git clone https://github.com/ChekovPavel/Nova.git
cd Nova
chmod +x scripts/setup.sh
./scripts/setup.sh
```

Das Skript führt alle folgenden Schritte automatisch aus.

---

### Option B: Manuelle Installation

#### Schritt 1 – Repository klonen

```bash
git clone https://github.com/ChekovPavel/Nova.git
cd Nova
```

#### Schritt 2 – Python Virtual Environment erstellen

```bash
# Venv erstellen
python3 -m venv .venv

# Aktivieren (Linux/macOS):
source .venv/bin/activate

# Aktivieren (Windows/WSL):
.venv\Scripts\activate
```

> Nach der Aktivierung siehst du `(.venv)` am Anfang der Kommandozeile.
> Du musst das Venv **bei jedem neuen Terminal** erneut aktivieren.

#### Schritt 3 – Basis-Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

#### Schritt 4 – Optionale Abhängigkeiten installieren

Je nach gewünschtem Feature-Set:

```bash
# Verschlüsselung (empfohlen – für sichere Datenspeicherung)
pip install cryptography

# Sprachausgabe / TTS (Nova kann sprechen)
pip install pyttsx3

# Spracheingabe / STT (Sprachsteuerung per Mikrofon)
pip install SpeechRecognition PyAudio

# Lokales Whisper STT (offline Spracherkennung – kein Cloud-Dienst)
pip install faster-whisper

# OpenAI-kompatibles SDK (für Cloud-LLM wie GPT-4o, Claude via API)
pip install openai

# Erweitertes NLP (bessere Sprachverarbeitung)
pip install spacy
python -m spacy download de_core_news_sm
```

> **Alles auf einmal installieren:**
> ```bash
> pip install -r requirements-full.txt
> python -m spacy download de_core_news_sm
> ```

##### PyAudio – Systemabhängigkeit

PyAudio benötigt die `PortAudio`-Bibliothek auf Systemebene:

```bash
# Ubuntu/Debian/Raspberry Pi:
sudo apt install portaudio19-dev

# macOS:
brew install portaudio

# Windows: Kein Schritt nötig (PyAudio enthält PortAudio für Windows)
```

#### Schritt 5 – Ollama installieren

Siehe [Abschnitt 5 – Ollama vollständige Einrichtung](#5-ollama-vollständige-einrichtung).

---

## 3. Beste KI-Modell-Empfehlung (Stand April 2026)

### 🏆 Lokale Modelle via Ollama

#### Für maximale Qualität (Gaming-PC, 24+ GB VRAM)

| Modell | Größe | Stärken |
|--------|-------|---------|
| **`llama3.1:70b`** | ~40 GB | Maximale lokale Qualität, hervorragendes Deutsch |
| **`qwen2.5:72b`** | ~45 GB | Exzellente Mehrsprachigkeit, sehr gut für Deutsch |

```bash
ollama pull llama3.1:70b
```

#### Für sehr gute Qualität (Gaming-PC, 12–16 GB VRAM)

| Modell | Größe | Stärken |
|--------|-------|---------|
| **`qwen2.5:14b`** ⭐ | ~8 GB | **Empfohlen:** Exzellentes Deutsch, gute Balance |
| **`llama3.3:70b-q4`** | ~40 GB (4-bit) | Hohe Qualität in 4-bit-Quantisierung |
| **`mistral:7b`** | ~4 GB | Schnell, effizient |

```bash
ollama pull qwen2.5:14b
```

#### Für gute Balance (Gaming-PC, 8 GB VRAM) ⭐ Empfehlung für die meisten Nutzer

| Modell | Größe | Stärken |
|--------|-------|---------|
| **`llama3.1:8b`** ⭐ | ~4.7 GB | **Beste Balance aus Qualität und Geschwindigkeit** |
| **`mistral:7b`** | ~4.1 GB | Etwas schneller, sehr gute Qualität |
| **`gemma3:9b`** | ~5 GB | Google-Modell, gute multimodale Fähigkeiten |

```bash
ollama pull llama3.1:8b
```

> **Empfehlung für Gaming-PC:** `llama3.1:8b` ist der ideale Einstieg – läuft
> flüssig mit 8 GB VRAM, liefert sehr gute Antwortqualität und ist optimal auf
> Deutsch abgestimmt (Llama 3.1 hat starke mehrsprachige Fähigkeiten).

#### Für Raspberry Pi / schwache Hardware

| Modell | Größe | Stärken |
|--------|-------|---------|
| **`llama3.2:1b`** | ~700 MB | Sehr schnell, minimal, für Pi 4B+ 4 GB |
| **`llama3.2:3b`** | ~2 GB | Gute Qualität, für Pi 4B+ 8 GB |
| **`phi3.5:mini`** | ~2.2 GB | Microsoft-Modell, sehr effizient |
| **`gemma2:2b`** | ~1.6 GB | Google-Modell, kompakt |

```bash
ollama pull llama3.2:1b     # Für Pi 4 mit 4 GB RAM
ollama pull llama3.2:3b     # Für Pi 4 mit 8 GB RAM / Pi 5
```

---

### ☁️ Cloud-Modelle via API

Falls du keine lokale Hardware nutzen möchtest oder maximale Qualität benötigst,
kannst du externe Cloud-APIs verwenden. Diese erfordern einen API-Key.

| Modell | Anbieter | Qualität | Kosten |
|--------|---------|---------|--------|
| **GPT-4o** | OpenAI | ⭐⭐⭐⭐⭐ | ~$2.50 / 1M Tokens (Input) |
| **GPT-4.1** | OpenAI | ⭐⭐⭐⭐⭐ | ~$2.00 / 1M Tokens (Input) |
| **Claude Opus 4** | Anthropic | ⭐⭐⭐⭐⭐ | ~$15.00 / 1M Tokens (Input) |
| **Claude Sonnet 4.5** | Anthropic | ⭐⭐⭐⭐½ | ~$3.00 / 1M Tokens (Input) |
| **Gemini 2.5 Pro** | Google | ⭐⭐⭐⭐⭐ | ~$1.25 / 1M Tokens (Input) |
| **GPT-4o-mini** | OpenAI | ⭐⭐⭐⭐ | ~$0.15 / 1M Tokens (Input) |

> **Empfehlung für Cloud:** **GPT-4o** oder **Claude Sonnet 4.5** – beide
> bieten exzellente Deutsch-Unterstützung und sind ideal für Nova.

Konfiguration in `config.json`:

```json
"api": {
    "enabled": true,
    "llm_endpoint": "https://api.openai.com/v1/chat/completions",
    "llm_api_key": "sk-DEIN_KEY_HIER",
    "llm_model": "gpt-4o"
}
```

Oder über Umgebungsvariablen (empfohlen für Sicherheit):

```bash
export NOVA_LLM_API_KEY="sk-DEIN_KEY_HIER"
export NOVA_LLM_ENDPOINT="https://api.openai.com/v1/chat/completions"
```

---

## 4. Konfiguration Schritt für Schritt

### 4.1 config.json erstellen

```bash
cp config.json.example config.json
```

### 4.2 Secret Key generieren

Der Secret Key wird für die Verschlüsselung der Datenbank genutzt.
**Bewahre ihn sicher auf – ohne ihn sind verschlüsselte Daten verloren!**

```bash
# Mit openssl (empfohlen):
openssl rand -hex 32

# Alternative (mit Python):
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Den generierten Key in `config.json` eintragen:

```json
"secret_key": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678"
```

### 4.3 Datenbank-Pfad setzen

Setze `db_path` auf einen Pfad **außerhalb** des Git-Repos:

```json
"db_path": "~/nova_data/nova_data.db"
```

```bash
# Verzeichnis anlegen:
mkdir -p ~/nova_data
```

### 4.4 Ollama-Konfiguration

```json
"ollama": {
    "host": "http://localhost:11434",
    "model": "llama3.1:8b",
    "temperature": 0.7,
    "max_tokens": 512
}
```

| Einstellung | Empfehlung | Beschreibung |
|-------------|-----------|-------------|
| `host` | `http://localhost:11434` | Ollama läuft lokal |
| `model` | `llama3.1:8b` (8 GB VRAM) | Modellname wie in `ollama pull` |
| `temperature` | `0.7` | Kreativität (0.0 = deterministisch, 1.0 = sehr kreativ) |
| `max_tokens` | `512` (Pi) / `2048` (PC) | Maximale Antwortlänge |

### 4.5 Voice-Konfiguration

```json
"voice": {
    "enabled": true,
    "language": "de-DE",
    "tts_rate": 160,
    "tts_volume": 0.9
}
```

> Sprachausgabe erfordert `pip install pyttsx3`.
> Spracheingabe erfordert `pip install SpeechRecognition PyAudio`.

### 4.6 Backup-Konfiguration

```json
"backup": {
    "enabled": true,
    "dir": "~/nova_backups",
    "max_backups": 30,
    "interval_sec": 3600
}
```

```bash
# Backup-Verzeichnis anlegen:
mkdir -p ~/nova_backups
```

### 4.7 API-Konfiguration (Cloud-LLM, optional)

```json
"api": {
    "enabled": false,
    "llm_endpoint": "https://api.openai.com/v1/chat/completions",
    "llm_api_key": "sk-DEIN_KEY_HIER",
    "llm_model": "gpt-4o"
}
```

> Setze `"enabled": true` nur, wenn du einen gültigen API-Key hast.
> Nova nutzt Ollama als primäres Backend; die API ist nur als Fallback gedacht.

### 4.8 Vollständiges config.json Beispiel (Gaming-PC)

```json
{
  "db_path": "~/nova_data/nova_data.db",
  "secret_key": "HIER_DEINEN_GENERIERTEN_KEY_EINTRAGEN",
  "stm_capacity": 50,
  "ollama": {
    "host": "http://localhost:11434",
    "model": "llama3.1:8b",
    "temperature": 0.7,
    "max_tokens": 2048
  },
  "local_stt": {
    "whisper_model": "medium",
    "device": "cuda",
    "compute_type": "float16",
    "language": "de"
  },
  "backup": {
    "enabled": true,
    "dir": "~/nova_backups",
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
```

---

## 5. Ollama vollständige Einrichtung

### 5.1 Installation

#### Linux (empfohlen)

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### macOS

```bash
# Option 1: Installer herunterladen
# → https://ollama.ai → "Download" → macOS

# Option 2: Homebrew
brew install ollama
```

#### Windows

1. Installer herunterladen: [https://ollama.ai](https://ollama.ai) → "Download" → Windows
2. `.exe`-Datei ausführen und Installation abschließen.
3. Ollama läuft automatisch als Hintergrundprozess.

#### WSL2 (Windows Subsystem for Linux)

```bash
# In WSL2-Terminal:
curl -fsSL https://ollama.com/install.sh | sh
```

### 5.2 Modell herunterladen

```bash
# Modell herunterladen (Beispiele):
ollama pull llama3.1:8b      # Empfehlung für Gaming-PC mit 8 GB VRAM
ollama pull llama3.2:1b      # Für Raspberry Pi / schwache Hardware
ollama pull qwen2.5:14b      # Für 12 GB VRAM, sehr gutes Deutsch

# Alle heruntergeladenen Modelle anzeigen:
ollama list
```

### 5.3 CUDA / GPU-Beschleunigung aktivieren (NVIDIA)

Ollama erkennt NVIDIA-GPUs automatisch, wenn das CUDA Toolkit installiert ist:

```bash
# 1. NVIDIA-Treiber prüfen:
nvidia-smi

# 2. CUDA Toolkit installieren (falls nicht vorhanden):
# → https://developer.nvidia.com/cuda-downloads
# Empfohlen: CUDA 12.x

# 3. Ollama neu starten:
sudo systemctl restart ollama  # Linux mit systemd
# oder:
pkill ollama && ollama serve   # Manuell
```

Nach der GPU-Einrichtung wird Ollama automatisch die GPU nutzen. Prüfen:

```bash
ollama ps   # Zeigt aktive Modelle und ob GPU genutzt wird
```

### 5.4 Ollama als Service starten (Linux)

```bash
# Service aktivieren und starten:
sudo systemctl enable ollama
sudo systemctl start ollama

# Status prüfen:
sudo systemctl status ollama

# Logs anzeigen:
journalctl -u ollama -f
```

### 5.5 Testen ob Ollama läuft

```bash
# REST API prüfen:
curl http://localhost:11434/api/tags

# Schnelltest im Terminal:
ollama run llama3.1:8b "Hallo! Sag kurz Hallo auf Deutsch."

# Mit Python testen:
python3 -c "
import urllib.request, json
req = urllib.request.urlopen('http://localhost:11434/api/tags')
data = json.loads(req.read())
print('Verfügbare Modelle:', [m['name'] for m in data.get('models', [])])
"
```

---

## 6. Nova starten und testen

### 6.1 Konsolenmodus

```bash
# Venv aktivieren (falls noch nicht aktiv):
source .venv/bin/activate

# Nova starten:
python main.py
```

### 6.2 GUI-Modus (Tkinter)

```bash
python main.py --gui
```

> Tkinter ist Teil der Python-Standardbibliothek. Auf Ubuntu ggf.:
> `sudo apt install python3-tk`

### 6.3 Eigene Konfigurationsdatei

```bash
python main.py --config /pfad/zur/config.json
```

### 6.4 Docker-Modus

```bash
# Bauen und starten:
docker-compose up --build

# Im Hintergrund:
docker-compose up -d

# Logs verfolgen:
docker-compose logs -f
```

### 6.5 Erste Interaktion – Test-Befehle

Nach dem Start kannst du Nova sofort testen:

```
> Hallo Nova, wie geht es dir?
> arbeit                           # Wechselt in den Arbeitsmodus
> ich hab ein meeting über Budgets  # Meeting-Modus mit Agenda
> normal                           # Zurück zum Normalmodus
> flirten                          # Dating-Modus aktivieren
> fokus                            # Fokus-Modus (Konzentration)
> entspann                         # Relax-Modus
> schlaf                           # Sleep-Modus (minimale Aktivität)
> beenden                          # Nova beenden
```

#### Modi testen

| Modus | Aktivierungs-Keyword | Beschreibung |
|-------|---------------------|-------------|
| `normal` | `normal` | Standardmodus |
| `work` | `arbeit` | Sachlich, präzise |
| `relax` | `entspann`, `ruh` | Locker, warm |
| `focus` | `fokus` | Hochkonzentration |
| `empathy` | `empathi` | Emotional unterstützend |
| `sleep` | `schlaf` | Minimale Aktivität |
| `dating` | `date`, `flirt`, `romantisch` | Warm, verspielt, romantisch |
| `meeting` | `meeting`, `besprechung` | Konzise, strukturiert, Agenda |

#### Vollständiger Testlauf

```bash
# Terminal 1: Ollama starten (falls nicht als Service):
ollama serve

# Terminal 2: Nova starten:
source .venv/bin/activate
python main.py
```

Erwartete Ausgabe beim ersten Start:

```
Nova bereit. Eingabe: ...
> Hallo
Nova: Hallo! Wie kann ich dir helfen?
```

---

## 7. Troubleshooting

### 7.1 Ollama-Verbindungsprobleme

**Fehler:** `ConnectionRefusedError` oder `ollama connection failed`

```bash
# Läuft Ollama?
curl http://localhost:11434/api/tags
# → Wenn Fehler: Ollama starten mit:
ollama serve

# Oder als Service:
sudo systemctl start ollama
sudo systemctl status ollama

# Firewall-Problem (selten bei localhost):
sudo ufw allow 11434/tcp
```

**Ollama startet nicht:**

```bash
# Logs prüfen:
journalctl -u ollama -n 50
# oder:
ollama serve  # Direkt im Terminal starten, Fehlermeldungen lesen
```

### 7.2 Modell nicht gefunden

**Fehler:** `model not found` oder `pull model manifest: file does not exist`

```bash
# Verfügbare Modelle anzeigen:
ollama list

# Modell herunterladen:
ollama pull llama3.1:8b

# In config.json prüfen:
grep '"model"' config.json   # Muss mit 'ollama list' übereinstimmen
```

### 7.3 GPU / CUDA-Probleme

**Fehler:** CUDA-Fehler, GPU wird nicht erkannt

```bash
# NVIDIA-Treiber prüfen:
nvidia-smi
# Wenn Fehler: Treiber installieren (https://www.nvidia.com/drivers)

# CUDA-Version prüfen:
nvcc --version
# CUDA 12.x empfohlen

# Ollama GPU-Status prüfen:
ollama ps
# Spalte "PROCESSOR" sollte "GPU" anzeigen

# Falls CPU statt GPU genutzt wird:
# → CUDA-Toolkit installieren: https://developer.nvidia.com/cuda-downloads
# → Ollama neu installieren: curl -fsSL https://ollama.com/install.sh | sh

# Für faster-whisper mit GPU:
pip install faster-whisper
# In config.json setzen:
# "device": "cuda", "compute_type": "float16"
```

### 7.4 Datenbank-Probleme

**Fehler:** `sqlite3.OperationalError: unable to open database file`

```bash
# Datenbankverzeichnis anlegen:
mkdir -p ~/nova_data

# Berechtigungen prüfen:
ls -la ~/nova_data/

# db_path in config.json prüfen:
python3 -c "import json,os; c=json.load(open('config.json')); print(os.path.expanduser(c['db_path']))"
```

**Fehler:** `cryptography` nicht installiert (Verschlüsselungs-Warnung)

```bash
pip install cryptography
# Dann Nova neu starten
```

### 7.5 Python-Versionen / Virtual Environment

**Fehler:** `ModuleNotFoundError` nach `pip install`

```bash
# Prüfen ob das richtige Python/Venv aktiv ist:
which python     # Sollte auf .venv/bin/python zeigen
python --version # Sollte 3.10+ sein

# Venv neu aktivieren:
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Pakete im aktiven Venv prüfen:
pip list | grep cryptography
```

**Fehler:** `python: command not found` (Debian/Ubuntu)

```bash
sudo apt install python3 python3-pip python3-venv
# Dann mit 'python3' statt 'python' aufrufen:
python3 main.py
```

### 7.6 Sprachausgabe (TTS) funktioniert nicht

```bash
# pyttsx3 installieren:
pip install pyttsx3

# Linux: espeak-ng installieren:
sudo apt install espeak-ng libespeak-ng1

# macOS: Ist nativ verfügbar (keine Systemabhängigkeit nötig)

# Test:
python3 -c "import pyttsx3; e=pyttsx3.init(); e.say('Hallo'); e.runAndWait()"
```

### 7.7 Spracheingabe (STT) / PyAudio funktioniert nicht

```bash
# Systemabhängigkeit installieren:
sudo apt install portaudio19-dev  # Linux/Debian
brew install portaudio             # macOS

# PyAudio installieren:
pip install PyAudio

# Mikrofon-Berechtigungen prüfen (Linux):
arecord -l  # Zeigt verfügbare Aufnahmegeräte
```

### 7.8 Tkinter / GUI-Fehler

**Fehler:** `ModuleNotFoundError: No module named '_tkinter'`

```bash
# Ubuntu/Debian:
sudo apt install python3-tk

# Fedora/RHEL:
sudo dnf install python3-tkinter

# macOS: Tkinter ist in Python-Paketen von python.org enthalten
# Homebrew Python: brew install python-tk
```

### 7.9 Speicher- und Performance-Probleme

**Problem:** Nova reagiert sehr langsam

- Nutze ein kleineres Modell (z.B. `llama3.2:1b` statt `llama3.1:8b`)
- Reduziere `max_tokens` in `config.json` auf `256`
- Prüfe ob Ollama die GPU nutzt: `ollama ps`
- Schließe andere Programme die viel RAM verbrauchen

**Problem:** `out of memory` / Absturz

```bash
# Kleineres Modell verwenden:
ollama pull llama3.2:1b
# In config.json anpassen:
# "model": "llama3.2:1b"
```

---

## Schnellreferenz – Wichtige Befehle

```bash
# Nova starten:
source .venv/bin/activate && python main.py

# Ollama starten:
ollama serve

# Modell herunterladen:
ollama pull llama3.1:8b

# Secret Key generieren:
openssl rand -hex 32

# Datenbank-Verzeichnis anlegen:
mkdir -p ~/nova_data ~/nova_backups

# Alle Abhängigkeiten auf einmal:
pip install -r requirements-full.txt

# Tests ausführen:
python -m pytest tests/ -v
```
