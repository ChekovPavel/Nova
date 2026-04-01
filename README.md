# Nova – Persönlicher KI-Assistent

Nova ist ein vollständiger, modularer persönlicher KI-Assistent mit
Persönlichkeit, Gedächtnis, Emotionen und einem sozialen Sicherheitsnetz.

## Schnellstart

```bash
pip install cryptography          # optional: starke Verschlüsselung
python main.py                    # Konsolenmodus
python main.py --gui              # GUI (Tkinter)
python main.py --config cfg.json  # eigene Konfiguration
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
| 8 | `nova/relationships/relationship.py` | Beziehungsmodell |
| 9 | `nova/memory/ltm.py` | Langzeitgedächtnis |
| 10 | `nova/memory/stm.py` | Kurzzeitgedächtnis |
| 11 | `nova/learning/learner.py` | Lernmechanismus |
| 12 | `nova/goals/goals.py` | Ziele & Motivation |
| 13 | `nova/reflection/self_reflection.py` | Selbstreflexion |
| 14 | `nova/modes/mode_manager.py` | Moduswechsel |
| 15 | `nova/voice/voice_io.py` | Sprach-I/O (TTS/STT) |
| 16 | `nova/persons/person_recognition.py` | Personenerkennung & Profiling |
| 17 | `nova/gui/interface.py` | GUI (Tkinter) |
| 18 | `nova/database/db_manager.py` | Datenbank & Persistenz |
| 19 | `nova/security/encryption.py` | Sicherheit & Verschlüsselung |
| 20 | `nova/api/external_services.py` | API / Externe Dienste |
| 21 | `nova/safety/social_safety.py` | SocialSafetyLayer |
| 22 | `nova/memory/storage_depth.py` | SpeicherTiefe-System |
| 23 | `nova/memory/relevance_filter.py` | RelevanzFilter / STM-Verarbeitung |

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
    "llm_model": "gpt-4o-mini"
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
