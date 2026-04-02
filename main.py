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

from __future__ import annotations

import argparse
import json
import logging
import os


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def load_config(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        logging.error("Konfigurationsfehler in %s: %s", path, exc)
        return {}


def build_config(args: argparse.Namespace) -> dict:
    """Baut die Konfiguration aus Datei + Umgebungsvariablen."""
    cfg = load_config(args.config) if hasattr(args, "config") and args.config else {}

    # Umgebungsvariablen überschreiben Datei-Werte
    if "NOVA_SECRET_KEY" in os.environ:
        cfg["secret_key"] = os.environ["NOVA_SECRET_KEY"]
    if "NOVA_LLM_API_KEY" in os.environ:
        cfg.setdefault("api", {})["llm_api_key"] = os.environ["NOVA_LLM_API_KEY"]
    if "NOVA_LLM_ENDPOINT" in os.environ:
        cfg.setdefault("api", {})["llm_endpoint"] = os.environ["NOVA_LLM_ENDPOINT"]

    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(description="Nova - Persönlicher KI-Assistent")
    parser.add_argument(
        "--gui", action="store_true", help="GUI-Modus starten (Tkinter)"
    )
    parser.add_argument(
        "--config", default="config.json", help="Pfad zur Konfigurationsdatei"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log-Level",
    )
    parser.add_argument(
        "--db",
        default="nova_data.db",
        help="Pfad zur Datenbankdatei",
    )
    args = parser.parse_args()

    setup_logging(args.log_level)
    cfg = build_config(args)
    cfg.setdefault("db_path", args.db)

    from nova.core.nova import Nova

    nova = Nova.create(cfg)

    if args.gui:
        from nova.gui.interface import NovaGUI

        gui = NovaGUI(nova)
        gui.start()
    else:
        try:
            nova.start()
        finally:
            nova.shutdown()


if __name__ == "__main__":
    main()
