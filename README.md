# Nova – Persönlicher KI-Assistent

Nova ist ein vollständiger, modularer persönlicher KI-Assistent mit
Persönlichkeit, Gedächtnis, Emotionen und einem sozialen Sicherheitsnetz.
Unterstützt getrennte Kontextprofile für **Dating** und **Arbeit**.

## Installation & Schnellstart

### Windows

```cmd
:: 1. In den Projektordner wechseln (Pfad ggf. anpassen)
cd C:\Users\nicki\Documents\Nova-main\Nova-main

:: 2. Konfigurationsdatei anlegen
copy config.json.example config.json

:: 3. Paket installieren (einmalig – danach von überall nutzbar)
pip install -e .

:: 4. Nova starten
python -m nova           :: Konsolenmodus
python -m nova --gui     :: GUI (Tkinter)
nova                     :: Kurzbefehl nach Installation
```

### Linux / macOS

```bash
# 1. In den Projektordner wechseln
cd /path/to/Nova-main

# 2. Konfigurationsdatei anlegen
cp config.json.example config.json

# 3. Paket installieren (einmalig)
pip install -e .

# 4. Nova starten
python -m nova        # Konsolenmodus
python -m nova --gui  # GUI (Tkinter)
nova                  # Kurzbefehl nach Installation
```

> **Hinweis:** `pip install -e .` muss **im Projektordner** (wo `pyproject.toml` liegt)
> ausgeführt werden, nicht im Home-Verzeichnis.

### Ohne Installation (direkter Aufruf aus dem Projektordner)

```cmd
cd C:\Users\nicki\Documents\Nova-main\Nova-main
copy config.json.example config.json
python main.py
python main.py --gui
python main.py --config config.json
```

### Optionale Abhängigkeiten

```cmd
pip install cryptography   :: starke Verschlüsselung
pip install openai         :: LLM-Backend (OpenAI/Ollama)
pip install pyttsx3 SpeechRecognition  :: Sprach-I/O
```

## Architektur (Kapitelübersicht)

| Kap. | Modul | Beschreibung |
|------|-------|-------------|
| 1 | `nova/core/nova.py` | Grundstruktur / Architektur |
| 2 | `nova/core/main_loop.py` | Kernlogik / Hauptschleife |
| 3 | `nova/nlp/processor.py` | Sprachverarbeitung / NLP |
| 4 | `nova/nlp/response.py` | Antwortgenerierung |
| 5 | `nova/context/context_manager.py` | Kontext-Management |
| 6 | `nova/personality/personality.py` | Persönlichkeitsmodell (Big Five) |
| 7 | `nova/personality/emotion.py` | Emotionsschicht (VAD-Modell) |
| 8 | `nova/relationships/relationship.py` | Beziehungsmodell (inkl. Dating-Profil & Timeline) |
| 9 | `nova/memory/ltm.py` | Langzeitgedächtnis |
| 10 | `nova/memory/stm.py` | Kurzzeitgedächtnis |
| 11 | `nova/learning/learner.py` | Lernmechanismus |
| 12 | `nova/goals/goals.py` | Ziele & Motivation |
| 13 | `nova/reflection/self_reflection.py` | Selbstreflexion & Meeting-Zusammenfassung |
| 14 | `nova/modes/mode_manager.py` | Moduswechsel (inkl. dating & meeting) |
| 15 | `nova/voice/voice_io.py` | Sprach-I/O (TTS/STT) |
| 16 | `nova/persons/person_recognition.py` | Personenerkennung & Profiling |
| 17 | `nova/gui/interface.py` | GUI (Tkinter) |
| 18 | `nova/database/db_manager.py` | Datenbank & Persistenz |
| 19 | `nova/security/encryption.py` | Sicherheit & Verschlüsselung |
| 20 | `nova/api/external_services.py` | API / Externe Dienste (inkl. Kalender-Stub) |
| 21 | `nova/safety/social_safety.py` | SocialSafetyLayer |
| 22 | `nova/memory/storage_depth.py` | SpeicherTiefe-System |
| 23 | `nova/memory/relevance_filter.py` | RelevanzFilter / STM-Verarbeitung |
| 24 | `nova/profiles/profile_manager.py` | Kontextprofil-Trennung (privat / Arbeit) |
| 25 | `nova/suggestions/suggestion_engine.py` | Vorschlags-Engine (Dating & Arbeit) |

## Modi

| Modus | Aktivierung (Keyword) | Kontext | Beschreibung |
|-------|----------------------|---------|-------------|
| `normal` | „normal" | privat | Standardmodus |
| `work` | „arbeit" | Arbeit | Sachlich und präzise |
| `relax` | „entspann", „ruh" | privat | Locker und warm |
| `focus` | „fokus" | Arbeit | Hochkonzentration |
| `empathy` | „empathi" | privat | Emotional unterstützend |
| `sleep` | „schlaf" | privat | Minimale Aktivität |
| **`dating`** | **„date", „flirt", „romantisch", „verliebt"** | **privat** | **Warm, verspielt, romantisch** |
| **`meeting`** | **„meeting", „besprechung", „konferenz"** | **Arbeit** | **Konzise, strukturiert, Agenda** |

### Privat ↔ Arbeit – Kontexttrennung

Nova schaltet automatisch zwischen zwei getrennten Profilen um:
- **Privates Profil** (`private`): Dating, Relax, Normal, Empathy, Sleep
- **Arbeitsprofil** (`work`): Work, Meeting, Focus

Jedes Profil hat einen **eigenen STM** – private und berufliche Gespräche
mischen sich nie.  LTM-Einträge werden mit dem Profil-Tag versehen
(`profile:private` / `profile:work`).

### Dating-Modus

```
Du: ich möchte flirten
Nova: [Dating-Modus, emotionssensitiv, verspielt]
      💘 Date-Ideen für [Person]:
        1. Livekonzert besuchen
        2. Kochkurs zusammen besuchen
        ...
```

- Emotionssensitivität: 95 %
- Kommunikationsstil: warm-verspielt, hoher Humor, Komplimente aktiviert
- Date-Ideen basierend auf den gespeicherten Interessen der Person
- Beziehungsstatus-Tracking: `stranger → acquaintance → crush → dating → partner`

### Meeting-Modus

```
Du: ich hab ein meeting
Nova: [Meeting-Modus]
      📋 Meeting-Agenda: [Thema]
        1. Begrüßung & Ziele (5 min)
        2. Hauptthema ...
        ...
```

- Beim **Verlassen** des Meeting-Modus wird automatisch eine Zusammenfassung
  erstellt und im LTM gespeichert.
- Agenda-Vorschläge mit Thema und Teilnehmern.

## Personen & Beziehungen

Das Personenprofil wurde um Dating-Felder erweitert:

| Feld | Beschreibung |
|------|-------------|
| `relationship_status` | `stranger / acquaintance / crush / dating / partner / ex / colleague / friend` |
| `interests` | Liste von Interessen (Basis für Date-Ideen) |
| `date_ideas` | Gespeicherte Date-Ideen für diese Person |
| `compatibility_notes` | Freitext-Notizen zur Kompatibilität |

Alle Felder werden über die vorhandene `profile`-Struktur gespeichert.
Zusätzlich gibt es eine **Ereignis-Timeline** (`person_timeline`) für
Dates, Meetings und Meilensteine.

## Konfiguration

`config.json` (Beispiel):
```json
{
  "db_path": "nova_data.db",
  "secret_key": "mein-geheimes-passwort",
  "stm_capacity": 20,
  "api": {
    "llm_endpoint": "https://api.openai.com/v1/chat/completions",
    "llm_api_key": "sk-...",
    "llm_model": "gpt-4o-mini",
    "calendar_endpoint": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
    "calendar_api_key": "google-oauth-token"
  },
  "voice": {
    "enabled": true,
    "language": "de-DE",
    "tts_rate": 175
  }
}
```

Alternativ via Umgebungsvariablen:
```bash
export NOVA_SECRET_KEY="mein-geheimes-passwort"
export NOVA_LLM_API_KEY="sk-..."
export NOVA_LLM_ENDPOINT="https://api.openai.com/v1/chat/completions"
```

