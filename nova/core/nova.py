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
        self.person_recognition = None
        self.social_safety = None
        self.api_client = None
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
        from nova.persons.person_recognition import PersonRecognition
        from nova.safety.social_safety import SocialSafetyLayer
        from nova.api.external_services import ExternalServices
        from nova.core.main_loop import MainLoop

        nova = cls(config)
        cfg = nova.config

        logger.info("Nova wird initialisiert …")

        # Persistenz & Sicherheit zuerst
        nova.db = DatabaseManager(cfg.get("db_path", "nova_data.db"))
        nova.security = SecurityManager(cfg.get("secret_key"))

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
        nova.response_generator = ResponseGenerator(
            nova.personality,
            nova.emotion,
            nova.context_manager,
            nova.social_safety,
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

        # Externe Dienste
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
