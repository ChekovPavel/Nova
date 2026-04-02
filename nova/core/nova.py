"""
Kapitel 1 – Grundstruktur / Architektur Nova

Nova ist ein persönlicher KI-Assistent mit Persönlichkeit, Gedächtnis,
Emotionen und einem sozialen Sicherheitsnetz.  Dieses Modul definiert
die zentrale Nova-Klasse, die alle Subsysteme zusammenhält.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Konfigurationsvalidierung
# ------------------------------------------------------------------

_CONFIG_SCHEMA: dict[str, dict[str, Any]] = {
    "db_path": {"type": str, "default": "nova_data.db"},
    "secret_key": {"type": str, "default": None},
    "stm_capacity": {"type": int, "default": 20, "min": 1, "max": 500},
    "backup": {
        "type": dict,
        "default": {},
        "fields": {
            "enabled": {"type": bool, "default": True},
            "dir": {"type": str, "default": "~/nova_backups"},
            "max_backups": {"type": int, "default": 30, "min": 1, "max": 365},
            "interval_sec": {"type": (int, float), "default": 3600, "min": 60},
        },
    },
    "ollama": {
        "type": dict,
        "default": {},
        "fields": {
            "host": {"type": str, "default": "http://localhost:11434"},
            "model": {"type": str, "default": "llama3.2:1b"},
            "temperature": {"type": (int, float), "default": 0.7, "min": 0.0, "max": 2.0},
            "max_tokens": {"type": int, "default": 512, "min": 1},
        },
    },
    "voice": {"type": dict, "default": {}},
    "api": {"type": dict, "default": {}},
    "local_stt": {"type": dict, "default": {}},
    "web_search": {"type": dict, "default": {}},
}


def validate_config(cfg: dict) -> dict:
    """
    Validiert und ergänzt fehlende Standardwerte in der Konfiguration.

    Ungültige Werte werden durch Standardwerte ersetzt und geloggt.
    Gibt die bereinigte Konfiguration zurück.
    """
    validated = dict(cfg)

    for key, spec in _CONFIG_SCHEMA.items():
        value = validated.get(key)
        expected_type = spec["type"]
        default = spec["default"]

        # Fehlende Schlüssel → Standardwert
        if value is None and key not in validated:
            validated[key] = default
            continue

        # Typprüfung (None-Werte erlaubt falls default=None)
        if value is not None and not isinstance(value, expected_type):
            logger.warning(
                "Konfiguration: %r hat ungültigen Typ %s (erwartet %s), "
                "verwende Standard %r",
                key, type(value).__name__,
                expected_type.__name__ if isinstance(expected_type, type)
                else str(expected_type),
                default,
            )
            validated[key] = default
            continue

        # Wertebereichsprüfung für numerische Felder
        if isinstance(value, (int, float)):
            min_val = spec.get("min")
            max_val = spec.get("max")
            if min_val is not None and value < min_val:
                logger.warning(
                    "Konfiguration: %r=%r unter Minimum %r, verwende Minimum",
                    key, value, min_val,
                )
                validated[key] = min_val
            elif max_val is not None and value > max_val:
                logger.warning(
                    "Konfiguration: %r=%r über Maximum %r, verwende Maximum",
                    key, value, max_val,
                )
                validated[key] = max_val

        # Unter-Schema für verschachtelte Dicts
        if isinstance(value, dict) and "fields" in spec:
            for sub_key, sub_spec in spec["fields"].items():
                sub_val = value.get(sub_key)
                sub_default = sub_spec["default"]
                sub_type = sub_spec["type"]

                if sub_val is None and sub_key not in value:
                    continue  # Standardwerte werden von den Subsystemen gesetzt

                if sub_val is not None and not isinstance(sub_val, sub_type):
                    logger.warning(
                        "Konfiguration: %s.%s hat ungültigen Typ, "
                        "verwende Standard %r",
                        key, sub_key, sub_default,
                    )
                    value[sub_key] = sub_default
                    continue

                if isinstance(sub_val, (int, float)):
                    sub_min = sub_spec.get("min")
                    sub_max = sub_spec.get("max")
                    if sub_min is not None and sub_val < sub_min:
                        logger.warning(
                            "Konfiguration: %s.%s=%r unter Minimum %r",
                            key, sub_key, sub_val, sub_min,
                        )
                        value[sub_key] = sub_min
                    elif sub_max is not None and sub_val > sub_max:
                        logger.warning(
                            "Konfiguration: %s.%s=%r über Maximum %r",
                            key, sub_key, sub_val, sub_max,
                        )
                        value[sub_key] = sub_max

    return validated


class Nova:
    """
    Zentrale Nova-Instanz.

    Alle Subsysteme werden hier instanziiert und miteinander verknüpft.
    Nova wird über ``Nova.create()`` erzeugt, um eine kontrollierte
    Initialisierungsreihenfolge zu gewährleisten.
    """

    # ------------------------------------------------------------------
    # Konstruktion
    # ------------------------------------------------------------------

    def __init__(self, config: dict | None = None) -> None:
        self.config: dict = config or {}
        self._initialized: bool = False

        # Subsystem-Referenzen werden von create() befüllt
        self.db = None
        self.security = None
        self.ltm = None
        self.stm = None
        self.storage_depth = None
        self.relevance_filter = None
        self.personality = None
        self.emotion = None
        self.relationships = None
        self.context_manager = None
        self.nlp_processor = None
        self.response_generator = None
        self.learner = None
        self.goals = None
        self.reflection = None
        self.mode_manager = None
        self.profile_manager = None
        self.suggestion_engine = None
        self.voice_io = None
        self.local_stt = None
        self.person_recognition = None
        self.profile_enricher = None
        self.web_search = None
        self.social_safety = None
        self.api_client = None
        self.ollama = None
        self.backup = None
        self.main_loop = None
        self.gui = None

    # ------------------------------------------------------------------
    # Fabrikmethode
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, config: dict | None = None) -> Nova:
        """Erzeugt und initialisiert eine vollständige Nova-Instanz."""
        from nova.api.external_services import ExternalServices
        from nova.api.ollama_client import OllamaClient
        from nova.api.web_search import WebSearch
        from nova.backup.backup_manager import BackupManager
        from nova.context.context_manager import ContextManager
        from nova.core.main_loop import MainLoop
        from nova.database.db_manager import DatabaseManager
        from nova.goals.goals import GoalManager
        from nova.learning.learner import Learner
        from nova.memory.ltm import LongTermMemory
        from nova.memory.relevance_filter import RelevanceFilter
        from nova.memory.stm import ShortTermMemory
        from nova.memory.storage_depth import StorageDepth
        from nova.modes.mode_manager import ModeManager
        from nova.nlp.processor import NLPProcessor
        from nova.nlp.response import ResponseGenerator
        from nova.personality.emotion import EmotionEngine
        from nova.personality.personality import Personality
        from nova.persons.person_recognition import PersonRecognition
        from nova.persons.profile_enricher import ProfileEnricher
        from nova.profiles.profile_manager import ProfileManager
        from nova.reflection.self_reflection import SelfReflection
        from nova.relationships.relationship import RelationshipModel
        from nova.safety.social_safety import SocialSafetyLayer
        from nova.security.encryption import SecurityManager
        from nova.suggestions.suggestion_engine import SuggestionEngine
        from nova.voice.local_stt import LocalSTT
        from nova.voice.voice_io import VoiceIO

        nova = cls(config)
        cfg = validate_config(nova.config)
        nova.config = cfg

        logger.info("Nova wird initialisiert …")

        # Persistenz & Sicherheit zuerst
        nova.db = DatabaseManager(cfg.get("db_path", "nova_data.db"))
        nova.security = SecurityManager(cfg.get("secret_key"))

        # Backup-System (startet Hintergrund-Thread)
        backup_cfg = cfg.get("backup", {})
        nova.backup = BackupManager(
            db_path=cfg.get("db_path", "nova_data.db"),
            backup_dir=backup_cfg.get("dir", "~/nova_backups"),
            max_backups=backup_cfg.get("max_backups", 30),
            interval_sec=backup_cfg.get("interval_sec", 3600),
            enabled=backup_cfg.get("enabled", True),
        )
        nova.backup.start()

        # Gedächtnis
        nova.ltm = LongTermMemory(nova.db, nova.security)
        nova.stm = ShortTermMemory(
            capacity=cfg.get("stm_capacity", 20)
        )
        nova.storage_depth = StorageDepth(nova.ltm, nova.stm)
        nova.relevance_filter = RelevanceFilter(nova.stm, nova.ltm)

        # Persönlichkeit & Emotionen
        nova.personality = Personality(nova.db)
        nova.emotion = EmotionEngine(nova.personality)

        # Beziehungen & Personen
        nova.relationships = RelationshipModel(nova.db)
        nova.person_recognition = PersonRecognition(nova.relationships)

        # Kontext
        nova.context_manager = ContextManager(
            nova.stm, nova.ltm, nova.relationships
        )

        # NLP & Antwortgenerierung
        nova.nlp_processor = NLPProcessor()
        nova.social_safety = SocialSafetyLayer()

        # Lokales LLM (Ollama) – hat Vorrang vor externem API
        ollama_cfg = cfg.get("ollama", {})
        nova.ollama = OllamaClient(
            host=ollama_cfg.get("host", "http://localhost:11434"),
            model=ollama_cfg.get("model", "llama3.2:1b"),
            temperature=ollama_cfg.get("temperature", 0.7),
            max_tokens=ollama_cfg.get("max_tokens", 512),
        )
        if nova.ollama.is_alive():
            logger.info("Ollama verfügbar: %s", nova.ollama.model)
        else:
            logger.info("Ollama nicht verfügbar – Fallback auf Regelantworten.")

        nova.response_generator = ResponseGenerator(
            nova.personality,
            nova.emotion,
            nova.context_manager,
            nova.social_safety,
            ollama_client=nova.ollama,
        )

        # Lernen, Ziele, Reflexion
        nova.learner = Learner(nova.ltm, nova.personality)
        nova.goals = GoalManager(nova.db)
        nova.reflection = SelfReflection(
            nova.personality, nova.emotion, nova.goals, nova.ltm
        )

        # Modi & Voice
        nova.mode_manager = ModeManager(nova.emotion)
        nova.profile_manager = ProfileManager(
            stm_capacity=cfg.get("stm_capacity", 20)
        )
        nova.voice_io = VoiceIO(cfg.get("voice", {}))

        # Lokales STT (Whisper / Vosk)
        stt_cfg = cfg.get("local_stt", {})
        nova.local_stt = LocalSTT(
            whisper_model=stt_cfg.get("whisper_model", "tiny"),
            whisper_device=stt_cfg.get("device", "cpu"),
            whisper_compute_type=stt_cfg.get("compute_type", "int8"),
            vosk_model_path=stt_cfg.get("vosk_model_path", ""),
            language=stt_cfg.get("language", "de"),
        )
        if nova.local_stt.available:
            logger.info("Lokales STT verfügbar: %s", nova.local_stt.backend_name)
            nova.voice_io.set_local_stt(nova.local_stt)

        # Externe Dienste (Fallback, falls Ollama nicht verfügbar)
        nova.api_client = ExternalServices(cfg.get("api", {}))

        # Online-Suche (Kapitel 16.6 – kein API-Key erforderlich)
        web_cfg = cfg.get("web_search", {})
        nova.web_search = WebSearch(enabled=web_cfg.get("enabled", True))

        # Profil-Anreicherung (Kapitel 16.7 – auto-lernt aus Gesprächen)
        nova.profile_enricher = ProfileEnricher(nova.ltm)

        # Vorschlags-Engine
        nova.suggestion_engine = SuggestionEngine(nova.relationships, nova.goals)

        # Hauptschleife
        nova.main_loop = MainLoop(nova)

        nova._initialized = True
        logger.info("Nova erfolgreich initialisiert.")
        return nova

    # ------------------------------------------------------------------
    # Lebenszyklus
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Startet Nova (Hauptschleife)."""
        if not self._initialized:
            raise RuntimeError("Nova wurde nicht über Nova.create() erzeugt.")
        self.main_loop.run()

    def shutdown(self) -> None:
        """Fährt Nova sauber herunter."""
        logger.info("Nova wird heruntergefahren …")
        # Finales Backup vor dem Herunterfahren
        if self.backup and self.backup.enabled:
            logger.info("Erstelle finales Backup …")
            self.backup.backup_now(label="shutdown")
            self.backup.stop()
        if self.db:
            self.db.close()
        if self.voice_io:
            self.voice_io.stop()
        logger.info("Nova heruntergefahren.")

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        status = "bereit" if self._initialized else "nicht initialisiert"
        return f"<Nova status={status}>"
