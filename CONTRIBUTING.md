# Beitragen zu Nova

Danke für dein Interesse an Nova! 🌟 Hier erfährst du, wie du beitragen kannst.

## Schnellstart

```bash
# Repository klonen
git clone https://github.com/ChekovPavel/Nova.git
cd Nova

# Virtuelle Umgebung erstellen
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Abhängigkeiten installieren
pip install cryptography>=41.0.0 pytest>=7.0.0 pytest-cov>=4.0.0
pip install pre-commit && pre-commit install

# Tests ausführen
python -m pytest tests/ -v
```

## Entwicklungsrichtlinien

### Code-Stil

- **Python 3.9+** (verwende `from __future__ import annotations`)
- **Type Hints** auf allen öffentlichen Funktionen und Methoden
- **Docstrings** auf Deutsch für alle Module, Klassen und öffentliche Methoden
- Linting: `ruff check .` – alle Regeln müssen bestanden werden
- Formatierung: `ruff format .`

### Projektstruktur

```
nova/
├── core/           # Nova-Klasse, Hauptschleife
├── nlp/            # NLP-Verarbeitung, Antwortgenerierung
├── memory/         # STM, LTM, Relevanzfilter
├── personality/    # Big Five, Emotionen
├── relationships/  # Personenerkennung, Beziehungen
├── modes/          # Betriebsmodi (normal, work, dating, …)
├── profiles/       # Kontextprofile (privat/Arbeit)
├── database/       # SQLite-Persistenz
├── security/       # Verschlüsselung
├── safety/         # Inhaltsfilter, Prompt-Injection-Schutz
├── api/            # Externe Dienste, Ollama, Websuche
├── backup/         # Automatisches Backup
├── voice/          # TTS/STT
└── gui/            # Tkinter-GUI
```

### Commits

- Commit-Nachrichten auf **Englisch**
- Format: `type: short description`
  - `feat:` – Neues Feature
  - `fix:` – Bugfix
  - `docs:` – Dokumentation
  - `test:` – Tests
  - `refactor:` – Code-Umstrukturierung
  - `chore:` – Build, CI, Abhängigkeiten

### Tests

- Jedes neue Feature braucht Tests in `tests/`
- Testdateien: `test_<module>.py`
- Mindest-Testabdeckung: 60%
- Tests ausführen: `python -m pytest tests/ -v --cov=nova`

### Pull Requests

1. Forke das Repository
2. Erstelle einen Feature-Branch: `git checkout -b feat/mein-feature`
3. Schreibe Tests für deine Änderungen
4. Stelle sicher, dass alle Tests bestehen
5. Erstelle einen Pull Request mit einer klaren Beschreibung

## Sicherheit

Falls du eine Sicherheitslücke findest, erstelle bitte **kein** öffentliches Issue.
Kontaktiere stattdessen die Maintainer direkt.

## Lizenz

Mit deinem Beitrag stimmst du zu, dass dein Code unter der [MIT-Lizenz](LICENSE) veröffentlicht wird.
