#!/usr/bin/env python3
"""
Nova - Persönlicher KI-Assistent
Einstiegspunkt

Verwendung:
    python main.py                  # Konsolenmodus
    python main.py --gui            # GUI-Modus (Tkinter)
    python main.py --config config.json

Umgebungsvariablen (optional):
    NOVA_LLM_API_KEY    - API-Schlüssel für LLM-Backend
    NOVA_LLM_ENDPOINT   - URL des LLM-Endpunkts
    NOVA_SECRET_KEY     - Verschlüsselungsschlüssel
"""

# Die eigentliche Logik liegt in nova/cli.py, damit das Paket nach
# ``pip install -e .`` auch über ``python -m nova`` und den ``nova``-Befehl
# gestartet werden kann.
from nova.cli import build_config, load_config, main, setup_logging

__all__ = ["build_config", "load_config", "main", "setup_logging"]

if __name__ == "__main__":
    main()
