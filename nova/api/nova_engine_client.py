"""
Nova Inference Engine - Python client

Wraps the nova_engine shared library (nova_engine.so / nova_engine.dylib)
via ctypes and exposes the same interface as OllamaClient so it can be used
as a drop-in Tier-0 LLM backend in nova/nlp/response.py.
"""

from __future__ import annotations

import ctypes
import logging
import os
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ctypes structures matching include/nova_engine.h
# ---------------------------------------------------------------------------


class _GenConfig(ctypes.Structure):
    _fields_ = [
        ("max_new_tokens", ctypes.c_uint32),
        ("temperature", ctypes.c_float),
        ("top_p", ctypes.c_float),
        ("top_k", ctypes.c_int32),
        ("seed", ctypes.c_uint32),
    ]


_OUTPUT_BUF_SIZE = 8192  # bytes - sufficient for typical responses


def _load_library(extra_dir: str | None = None) -> ctypes.CDLL | None:
    """Locate and load the nova_engine shared library."""
    ext = "dylib" if platform.system() == "Darwin" else "so"
    here = Path(__file__).resolve().parent  # nova/api/

    candidates: list[str] = []
    if extra_dir:
        candidates.append(os.path.join(extra_dir, f"nova_engine.{ext}"))

    # Search relative to this file: ../../engine/
    engine_dir = here.parent.parent / "engine"
    candidates += [
        str(engine_dir / f"nova_engine.{ext}"),
        str(engine_dir / "build" / f"nova_engine.{ext}"),
        f"nova_engine.{ext}",  # falls back to LD_LIBRARY_PATH / current dir
    ]

    for path in candidates:
        if os.path.exists(path):
            try:
                lib = ctypes.CDLL(path)
                _bind_api(lib)
                logger.debug("nova_engine: loaded from %s", path)
                return lib
            except OSError as exc:
                logger.debug("nova_engine: failed to load %s: %s", path, exc)

    return None


def _bind_api(lib: ctypes.CDLL) -> None:
    """Set argtypes / restype for all exported functions."""
    lib.nova_engine_version.restype = ctypes.c_char_p
    lib.nova_engine_version.argtypes = []

    lib.nova_engine_last_error.restype = ctypes.c_char_p
    lib.nova_engine_last_error.argtypes = []

    lib.nova_engine_create.restype = ctypes.c_void_p
    lib.nova_engine_create.argtypes = [ctypes.c_char_p, ctypes.c_uint32]

    lib.nova_engine_generate.restype = ctypes.c_int32
    lib.nova_engine_generate.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.POINTER(_GenConfig),
        ctypes.c_char_p,
        ctypes.c_size_t,
    ]

    lib.nova_engine_reset.restype = None
    lib.nova_engine_reset.argtypes = [ctypes.c_void_p]

    lib.nova_engine_destroy.restype = None
    lib.nova_engine_destroy.argtypes = [ctypes.c_void_p]


# ---------------------------------------------------------------------------
# Public client
# ---------------------------------------------------------------------------


class NovaEngineClient:
    """
    Python wrapper around the nova_engine shared library.

    Exposes the same chat() / generate() / is_alive() / reset_availability_cache()
    interface as OllamaClient so it can serve as a Tier-0 backend in Nova
    (on-device inference, no HTTP round-trip).
    """

    def __init__(self, config: dict) -> None:
        eng = config.get("nova_engine", {})
        self._model_path: str = eng.get("model_path", "")
        self._max_seq_len: int = int(eng.get("max_seq_len", 512))
        self._temperature: float = float(eng.get("temperature", 0.7))
        self._top_p: float = float(eng.get("top_p", 0.9))
        self._top_k: int = int(eng.get("top_k", 40))
        self._max_new: int = int(eng.get("max_new_tokens", 200))

        self._lib: ctypes.CDLL | None = _load_library(eng.get("lib_dir"))
        self._handle: int | None = None

        if self._lib is not None:
            model_bytes = self._model_path.encode() if self._model_path else b""
            handle = self._lib.nova_engine_create(
                model_bytes, ctypes.c_uint32(self._max_seq_len)
            )
            if handle:
                self._handle = handle
                ver = self._lib.nova_engine_version()
                logger.info(
                    "nova_engine bereit: %s (Modell: %s)",
                    ver.decode() if ver else "?",
                    self._model_path or "<standard>",
                )
            else:
                raw_err = self._lib.nova_engine_last_error()
                logger.warning(
                    "nova_engine_create fehlgeschlagen: %s",
                    raw_err.decode() if raw_err else "unbekannt",
                )
        else:
            logger.debug("nova_engine: Shared Library nicht gefunden - deaktiviert")

    # ------------------------------------------------------------------
    # Public interface (mirrors OllamaClient)
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        """Return True if the engine library is loaded and a model is ready."""
        return self._lib is not None and self._handle is not None

    def reset_availability_cache(self) -> None:
        """No-op: kept for interface compatibility with OllamaClient."""

    def generate(self, prompt: str) -> str | None:
        """Generate a completion for a plain-text prompt."""
        return self._run(prompt) if self.is_alive() else None

    def chat(
        self,
        user_input: str,
        history: list[dict] | None = None,
        extra_system: str = "",
    ) -> str | None:
        """
        Chat completion with optional message history.

        Builds a simple text prompt from the conversation history and
        appends a Nova: prefix to guide the model's response.
        """
        if not self.is_alive():
            return None

        parts: list[str] = []
        if extra_system:
            parts.append(f"[System] {extra_system}")
        for msg in history or []:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        parts.append(f"User: {user_input}")
        parts.append("Nova:")

        return self._run("\n".join(parts))

    def reset_context(self) -> None:
        """Reset the engine's generation state."""
        if self.is_alive():
            self._lib.nova_engine_reset(ctypes.c_void_p(self._handle))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self, prompt: str) -> str | None:
        cfg = _GenConfig(
            max_new_tokens=self._max_new,
            temperature=self._temperature,
            top_p=self._top_p,
            top_k=self._top_k,
            seed=42,
        )
        out_buf = ctypes.create_string_buffer(_OUTPUT_BUF_SIZE)
        n = self._lib.nova_engine_generate(
            ctypes.c_void_p(self._handle),
            prompt.encode("utf-8"),
            ctypes.byref(cfg),
            out_buf,
            ctypes.c_size_t(_OUTPUT_BUF_SIZE),
        )
        if n < 0:
            raw_err = self._lib.nova_engine_last_error()
            logger.warning(
                "nova_engine_generate Fehler: %s",
                raw_err.decode() if raw_err else "unbekannt",
            )
            return None
        return out_buf.value.decode("utf-8", errors="replace")

    def __del__(self) -> None:
        if self._lib and self._handle:
            self._lib.nova_engine_destroy(ctypes.c_void_p(self._handle))
            self._handle = None
