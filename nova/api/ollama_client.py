"""
Kapitel 24 - Lokales LLM via Ollama

Ollama stellt einen OpenAI-kompatiblen REST-Endpunkt lokal bereit.
Empfohlene Modelle für Raspberry Pi 4B+ (4-8 GB RAM):
  - llama3.2:1b   (~700 MB, sehr schnell)
  - llama3.2:3b   (~2 GB, gute Qualität)
  - phi3.5:mini   (~2.2 GB, Microsoft-Modell, sehr effizient)
  - gemma2:2b     (~1.6 GB, Google-Modell)
  - mistral:7b    (nur mit ≥8 GB RAM)

Ollama installieren (Pi/Linux):
    curl -fsSL https://ollama.com/install.sh | sh
    ollama pull llama3.2:1b      # Modell herunterladen

Ollama läuft dann auf http://localhost:11434 und bietet
eine OpenAI-kompatible API - Nova nutzt das direkt.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_DEFAULT_HOST = "http://localhost:11434"
# Timeout für LLM-Anfragen: 120 s deckt auch langsame Pi-Hardware ab.
# Für schnellere Hardware oder kleine Modelle kann dieser Wert über
# das config-Feld "ollama.timeout" reduziert werden.
_TIMEOUT = 120


class OllamaClient:
    """
    Leichtgewichtiger Client für einen lokal laufenden Ollama-Server.

    Unterstützt:
    - Chat-Completions (OpenAI-kompatibel, /api/chat)
    - Einfache Generierung (/api/generate)
    - Modell-Listing (/api/tags)
    - Health-Check
    """

    def __init__(
        self,
        host: str = _DEFAULT_HOST,
        model: str = "llama3.2:1b",
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        context_messages: int = 8,
        timeout: int = _TIMEOUT,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self._timeout = timeout
        self.system_prompt = system_prompt or (
            "Du bist Nova, ein freundlicher, empathischer, persönlicher "
            "KI-Assistent. Du läufst vollständig lokal auf einem Raspberry Pi "
            "und schützt die Privatsphäre des Nutzers. "
            "Antworte immer auf Deutsch, es sei denn der Nutzer schreibt Englisch. "
            "Sei präzise, warm und hilfsbereit."
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.context_messages = context_messages
        self._available: bool | None = None  # Cache

    # ------------------------------------------------------------------
    # Chat-Completions (Haupt-API)
    # ------------------------------------------------------------------

    def chat(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        extra_system: str = "",
    ) -> str | None:
        """
        Sendet eine Chat-Nachricht an Ollama und gibt die Antwort zurück.

        Args:
            user_input:   Nutzereingabe.
            history:      Vorherige Nachrichten als [{"role": ..., "content": ...}].
            extra_system: Zusätzlicher Kontext für den System-Prompt.

        Returns:
            Antworttext oder None bei Fehler.
        """
        system = self.system_prompt
        if extra_system:
            system = f"{system}\n\nKontext: {extra_system}"

        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history[-self.context_messages :])
        messages.append({"role": "user", "content": user_input})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        try:
            response = self._post(f"{self.host}/api/chat", payload)
            if response:
                content = response.get("message", {}).get("content", "").strip()
                if content:
                    return content
        except Exception as exc:
            logger.error("Ollama chat fehlgeschlagen: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Einfache Generierung (kein History-Management nötig)
    # ------------------------------------------------------------------

    def generate(self, prompt: str) -> str | None:
        """Einfache Prompt-Vervollständigung ohne Chat-History."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        try:
            response = self._post(f"{self.host}/api/generate", payload)
            if response:
                return response.get("response", "").strip()
        except Exception as exc:
            logger.error("Ollama generate fehlgeschlagen: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Modell-Verwaltung
    # ------------------------------------------------------------------

    def list_models(self) -> list[str]:
        """Gibt alle lokal verfügbaren Modelle zurück."""
        try:
            resp = self._get(f"{self.host}/api/tags")
            if resp:
                return [m["name"] for m in resp.get("models", [])]
        except Exception as exc:
            logger.warning("Ollama model list fehlgeschlagen: %s", exc)
        return []

    def model_available(self, model_name: str | None = None) -> bool:
        """Prüft, ob ein bestimmtes (oder das konfigurierte) Modell verfügbar ist."""
        name = model_name or self.model
        available = self.list_models()
        return any(name in m for m in available)

    # ------------------------------------------------------------------
    # Health-Check
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        """Prüft, ob der Ollama-Server erreichbar ist."""
        if self._available is not None:
            return self._available  # kurzes Caching
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                self._available = resp.status == 200
                return self._available
        except Exception:
            self._available = False
            return False

    def reset_availability_cache(self) -> None:
        """Setzt den Verfügbarkeits-Cache zurück (für Retry-Logik)."""
        self._available = None

    # ------------------------------------------------------------------
    # HTTP-Helfer
    # ------------------------------------------------------------------

    def _post(self, url: str, data: dict) -> dict | None:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode())

    def _get(self, url: str) -> dict | None:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        status = "erreichbar" if self.is_alive() else "nicht erreichbar"
        return f"<OllamaClient model={self.model!r} host={self.host!r} status={status}>"
