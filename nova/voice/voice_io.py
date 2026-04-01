"""
Kapitel 15 – Sprachein- & -ausgabe (Voice)

Kapselt Text-to-Speech (TTS) und Speech-to-Text (STT).
Nutzt pyttsx3 für TTS und SpeechRecognition für STT,
mit graceful Fallback auf reine Textein-/ausgabe.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# TTS
try:
    import pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False
    logger.info("pyttsx3 nicht installiert – TTS deaktiviert.")

# STT
try:
    import speech_recognition as sr
    _STT_AVAILABLE = True
except ImportError:
    _STT_AVAILABLE = False
    logger.info("SpeechRecognition nicht installiert – STT deaktiviert.")


class VoiceIO:
    """
    Sprachein- und -ausgabe für Nova.

    TTS: pyttsx3 (offline, plattformübergreifend)
    STT: Google Speech Recognition via SpeechRecognition
         (Fallback: Texteingabe über Konsole)
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        cfg = config or {}
        self._enabled = cfg.get("enabled", True)
        self._language = cfg.get("language", "de-DE")
        self._tts_rate = cfg.get("tts_rate", 175)
        self._tts_volume = cfg.get("tts_volume", 0.9)
        self._tts_voice_id: Optional[str] = cfg.get("voice_id")

        self._tts_engine = None
        self._tts_lock = threading.Lock()
        self._running = True

        if _TTS_AVAILABLE and self._enabled:
            self._init_tts()

        if _STT_AVAILABLE and self._enabled:
            self._recognizer = sr.Recognizer()
            self._microphone = sr.Microphone()
        else:
            self._recognizer = None
            self._microphone = None

    # ------------------------------------------------------------------
    # TTS-Initialisierung
    # ------------------------------------------------------------------

    def _init_tts(self) -> None:
        try:
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", self._tts_rate)
            self._tts_engine.setProperty("volume", self._tts_volume)
            # Stimme setzen, falls konfiguriert
            if self._tts_voice_id:
                self._tts_engine.setProperty("voice", self._tts_voice_id)
            else:
                # Erste deutsche Stimme suchen
                voices = self._tts_engine.getProperty("voices")
                for v in voices:
                    if v.languages and "de" in v.languages[0].lower():
                        self._tts_engine.setProperty("voice", v.id)
                        break
            logger.debug("TTS initialisiert.")
        except Exception as exc:
            logger.warning("TTS-Initialisierung fehlgeschlagen: %s", exc)
            self._tts_engine = None

    # ------------------------------------------------------------------
    # Sprechen
    # ------------------------------------------------------------------

    def speak(self, text: str) -> None:
        """Gibt Text als Sprache aus (non-blocking)."""
        if not self._enabled or not text:
            return
        if self._tts_engine:
            thread = threading.Thread(
                target=self._tts_speak_sync, args=(text,), daemon=True
            )
            thread.start()
        else:
            # Fallback: Text einfach loggen
            logger.info("TTS (Fallback): %s", text)

    def _tts_speak_sync(self, text: str) -> None:
        with self._tts_lock:
            try:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
            except Exception as exc:
                logger.warning("TTS-Fehler: %s", exc)

    def speak_sync(self, text: str) -> None:
        """Gibt Text synchron als Sprache aus (blockierend)."""
        if not self._enabled or not text:
            return
        if self._tts_engine:
            self._tts_speak_sync(text)

    # ------------------------------------------------------------------
    # Hören (STT)
    # ------------------------------------------------------------------

    def listen(self, timeout: float = 5.0) -> Optional[str]:
        """
        Hört auf Spracheingabe und gibt erkannten Text zurück.

        Args:
            timeout: Maximale Wartezeit in Sekunden.

        Returns:
            Erkannter Text oder None bei Fehler.
        """
        if not self._enabled or not _STT_AVAILABLE or not self._microphone:
            return None

        try:
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                logger.debug("Mikrofon aktiv, höre …")
                audio = self._recognizer.listen(source, timeout=timeout)
            text = self._recognizer.recognize_google(
                audio, language=self._language
            )
            logger.debug("STT erkannt: %r", text)
            return text
        except Exception as exc:
            logger.debug("STT-Fehler: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Einstellungen
    # ------------------------------------------------------------------

    def set_rate(self, rate: int) -> None:
        self._tts_rate = rate
        if self._tts_engine:
            self._tts_engine.setProperty("rate", rate)

    def set_volume(self, volume: float) -> None:
        self._tts_volume = max(0.0, min(1.0, volume))
        if self._tts_engine:
            self._tts_engine.setProperty("volume", self._tts_volume)

    def list_voices(self) -> list:
        if self._tts_engine:
            return self._tts_engine.getProperty("voices")
        return []

    # ------------------------------------------------------------------
    # Lebenszyklus
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Stoppt die TTS-Engine."""
        self._running = False
        if self._tts_engine:
            try:
                self._tts_engine.stop()
            except Exception:
                pass

    @property
    def tts_available(self) -> bool:
        return self._tts_engine is not None

    @property
    def stt_available(self) -> bool:
        return self._recognizer is not None
