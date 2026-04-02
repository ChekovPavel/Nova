"""
Kapitel 25 – Lokales STT (Speech-to-Text) via Faster-Whisper oder Vosk

Vollständig offline STT – kein Google, keine Cloud.

Optionen für Raspberry Pi 4B+:
  - faster-whisper (empfohlen): pip install faster-whisper
      Modelle: tiny (39 MB), base (74 MB), small (244 MB)
      Pi 4B+ (4GB): tiny oder base für Echtzeit
  - vosk (Alternative, sehr leicht):
      pip install vosk
      Deutsches Modell: https://alphacephei.com/vosk/models
      vosk-model-small-de-0.15 (~40 MB)

Dieses Modul ersetzt / ergänzt die Google-STT in voice_io.py.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
import wave

logger = logging.getLogger(__name__)

# Versuche faster-whisper zu importieren
try:
    from faster_whisper import WhisperModel
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False
    logger.info("faster-whisper nicht installiert.")

# Versuche vosk zu importieren
try:
    import vosk
    _VOSK_AVAILABLE = True
except ImportError:
    _VOSK_AVAILABLE = False
    logger.info("vosk nicht installiert.")

# PyAudio für Mikrofon-Zugriff
try:
    import pyaudio
    _PYAUDIO_AVAILABLE = True
except ImportError:
    _PYAUDIO_AVAILABLE = False
    logger.info("PyAudio nicht installiert – Mikrofon deaktiviert.")

# Basis-Audioparameter
_RATE = 16000
_CHANNELS = 1
_FORMAT_WIDTH = 2   # 16-bit = 2 Bytes
_CHUNK = 1024


class LocalSTT:
    """
    Offline-STT für Nova.

    Priorität:
    1. faster-whisper (wenn installiert)
    2. vosk (wenn installiert + Modell vorhanden)
    3. Fallback: None (Google-STT aus voice_io.py übernimmt)
    """

    def __init__(
        self,
        whisper_model: str = "tiny",
        whisper_device: str = "cpu",
        whisper_compute_type: str = "int8",
        vosk_model_path: str | None = None,
        language: str = "de",
    ) -> None:
        self.language = language
        self._whisper: object | None = None
        self._vosk_model: object | None = None
        self._backend: str | None = None

        if _WHISPER_AVAILABLE:
            self._init_whisper(whisper_model, whisper_device, whisper_compute_type)
        elif _VOSK_AVAILABLE and vosk_model_path:
            self._init_vosk(vosk_model_path)

    # ------------------------------------------------------------------
    # Initialisierung
    # ------------------------------------------------------------------

    def _init_whisper(
        self, model_size: str, device: str, compute_type: str
    ) -> None:
        try:
            logger.info(
                "Lade Whisper-Modell: %s (device=%s, compute=%s) …",
                model_size, device, compute_type,
            )
            self._whisper = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )
            self._backend = "whisper"
            logger.info("Whisper-Modell geladen.")
        except Exception as exc:
            logger.error("Whisper-Initialisierung fehlgeschlagen: %s", exc)

    def _init_vosk(self, model_path: str) -> None:
        if not os.path.isdir(model_path):
            logger.error("Vosk-Modellverzeichnis nicht gefunden: %s", model_path)
            return
        try:
            vosk.SetLogLevel(-1)
            self._vosk_model = vosk.Model(model_path)
            self._backend = "vosk"
            logger.info("Vosk-Modell geladen: %s", model_path)
        except Exception as exc:
            logger.error("Vosk-Initialisierung fehlgeschlagen: %s", exc)

    # ------------------------------------------------------------------
    # Haupt-Erkennungsmethode
    # ------------------------------------------------------------------

    def recognize_from_mic(self, duration: float = 5.0) -> str | None:
        """
        Nimmt ``duration`` Sekunden vom Mikrofon auf und gibt den Text zurück.

        Args:
            duration: Aufnahmedauer in Sekunden.

        Returns:
            Erkannter Text oder None.
        """
        if not _PYAUDIO_AVAILABLE:
            return None
        if not self._backend:
            return None

        audio_data = self._record_audio(duration)
        if not audio_data:
            return None

        return self.recognize_from_bytes(audio_data)

    def recognize_from_bytes(self, audio_bytes: bytes) -> str | None:
        """
        Erkennt Sprache aus 16-bit 16kHz mono PCM-Bytes.

        Args:
            audio_bytes: Rohe PCM-Bytes.

        Returns:
            Erkannter Text oder None.
        """
        if self._backend == "whisper":
            return self._recognize_whisper(audio_bytes)
        if self._backend == "vosk":
            return self._recognize_vosk(audio_bytes)
        return None

    def recognize_from_file(self, wav_path: str) -> str | None:
        """Erkennt Sprache aus einer WAV-Datei."""
        if self._backend == "whisper":
            try:
                segments, _ = self._whisper.transcribe(
                    wav_path,
                    language=self.language,
                    beam_size=1,
                    vad_filter=True,
                )
                return " ".join(s.text for s in segments).strip()
            except Exception as exc:
                logger.error("Whisper file-Erkennung fehlgeschlagen: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Whisper-Erkennung
    # ------------------------------------------------------------------

    def _recognize_whisper(self, audio_bytes: bytes) -> str | None:
        """Schreibt Bytes in temporäre WAV-Datei und ruft Whisper auf."""
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
                with wave.open(f, "wb") as wf:
                    wf.setnchannels(_CHANNELS)
                    wf.setsampwidth(_FORMAT_WIDTH)
                    wf.setframerate(_RATE)
                    wf.writeframes(audio_bytes)

            segments, _ = self._whisper.transcribe(
                tmp_path,
                language=self.language,
                beam_size=1,
                vad_filter=True,        # Stille wird übersprungen
            )
            text = " ".join(s.text for s in segments).strip()
            return text if text else None
        except Exception as exc:
            logger.error("Whisper-Erkennung fehlgeschlagen: %s", exc)
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)

    # ------------------------------------------------------------------
    # Vosk-Erkennung
    # ------------------------------------------------------------------

    def _recognize_vosk(self, audio_bytes: bytes) -> str | None:
        import json as _json
        try:
            rec = vosk.KaldiRecognizer(self._vosk_model, _RATE)
            rec.AcceptWaveform(audio_bytes)
            result = _json.loads(rec.FinalResult())
            text = result.get("text", "").strip()
            return text if text else None
        except Exception as exc:
            logger.error("Vosk-Erkennung fehlgeschlagen: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Audioaufnahme
    # ------------------------------------------------------------------

    def _record_audio(self, duration: float) -> bytes | None:
        """Nimmt Audio vom Mikrofon auf und gibt PCM-Bytes zurück."""
        if not _PYAUDIO_AVAILABLE:
            return None
        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=_CHANNELS,
                rate=_RATE,
                input=True,
                frames_per_buffer=_CHUNK,
            )
            frames = []
            n_chunks = int(_RATE / _CHUNK * duration)
            for _ in range(n_chunks):
                data = stream.read(_CHUNK, exception_on_overflow=False)
                frames.append(data)
            stream.stop_stream()
            stream.close()
            pa.terminate()
            return b"".join(frames)
        except Exception as exc:
            logger.error("Audioaufnahme fehlgeschlagen: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Eigenschaften
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return self._backend is not None

    @property
    def backend_name(self) -> str:
        return self._backend or "none"

    def __repr__(self) -> str:
        return f"<LocalSTT backend={self.backend_name!r} lang={self.language!r}>"
