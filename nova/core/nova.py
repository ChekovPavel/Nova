"""
Kapitel 1 – Grundstruktur / Architektur Nova

Nova ist ein persönlicher KI-Assistent mit Persönlichkeit, Gedächtnis,
Emotionen und einem sozialen Sicherheitsnetz.  Dieses Modul definiert
die zentrale Nova-Klasse, die alle Subsysteme zusammenhält.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


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

    def __init__(self, config: Optional[dict] = None) -> None:
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
        self.voice_io = None
        self.local_stt = None
        self.person_recognition = None
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
    def create(cls, config: Optional[dict] = None) -> "Nova":
        """Erzeugt und initialisiert eine vollständige Nova-Instanz."""
        from nova.database.db_manager import DatabaseManager
        from nova.security.encryption import SecurityManager
        from nova.memory.ltm import LongTermMemory
        from nova.memory.stm import ShortTermMemory
        from nova.memory.storage_depth import StorageDepth
        from nova.memory.relevance_filter import RelevanceFilter
        from nova.personality.personality import Personality
        from nova.personality.emotion import EmotionEngine
        from nova.relationships.relationship import RelationshipModel
        from nova.context.context_manager import ContextManager
        from nova.nlp.processor import NLPProcessor
        from nova.nlp.response import ResponseGenerator
        from nova.learning.learner import Learner
        from nova.goals.goals import GoalManager
        from nova.reflection.self_reflection import SelfReflection
        from nova.modes.mode_manager import ModeManager
        from nova.voice.voice_io import VoiceIO
        from nova.voice.local_stt import LocalSTT
        from nova.persons.person_recognition import PersonRecognition
        from nova.safety.social_safety import SocialSafetyLayer
        from nova.api.external_services import ExternalServices
        from nova.api.ollama_client import OllamaClient
        from nova.backup.backup_manager import BackupManager
        from nova.core.main_loop import MainLoop

        nova = cls(config)
        cfg = nova.config

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

        # Externe Dienste (Fallback, falls Ollama nicht verfügbar)
        nova.api_client = ExternalServices(cfg.get("api", {}))

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
