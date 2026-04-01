"""
Kapitel 20 – API / Externe Dienste

Ermöglicht Nova die Kommunikation mit externen APIs:
- LLM-Backend (OpenAI-kompatibel)
- Wetter-API
- Generische HTTP-Anfragen

Alle Anfragen sind optional – Nova funktioniert auch offline.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # Sekunden


class ExternalServices:
    """
    Bündelt externe API-Aufrufe.

    Alle Methoden kehren im Fehlerfall mit None / Fallback zurück.
    Es werden keine Secrets in Logs geschrieben.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self._llm_endpoint: Optional[str] = cfg.get("llm_endpoint")
        self._llm_api_key: Optional[str] = cfg.get("llm_api_key")
        self._llm_model: str = cfg.get("llm_model", "gpt-3.5-turbo")
        self._weather_api_key: Optional[str] = cfg.get("weather_api_key")
        self._enabled: bool = cfg.get("enabled", True)

    # ------------------------------------------------------------------
    # LLM-Vervollständigung
    # ------------------------------------------------------------------

    def complete(
        self,
        user_input: str,
        context: Optional[Dict] = None,
        system_prompt: str = (
            "Du bist Nova, ein freundlicher, empathischer persönlicher "
            "KI-Assistent. Antworte hilfreich, ehrlich und warmherzig."
        ),
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """
        Ruft ein LLM-Backend (OpenAI-kompatibel) auf.

        Returns:
            Antworttext oder None bei Fehler / deaktiviertem Dienst.
        """
        if not self._enabled or not self._llm_endpoint or not self._llm_api_key:
            return None

        messages = [{"role": "system", "content": system_prompt}]

        # Kontext einfügen
        if context:
            for msg in context.get("messages", [])[-6:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("text", "")})

        messages.append({"role": "user", "content": user_input})

        payload = {
            "model": self._llm_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = self._post_json(
                self._llm_endpoint,
                payload,
                headers={"Authorization": f"Bearer {self._llm_api_key}"},
            )
            if response:
                return (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
        except Exception as exc:
            logger.error("LLM-Anfrage fehlgeschlagen: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Wetter
    # ------------------------------------------------------------------

    def get_weather(self, city: str) -> Optional[str]:
        """
        Ruft aktuelle Wetterdaten für eine Stadt ab (OpenWeatherMap).

        Returns:
            Menschenlesbarer Wetterstring oder None.
        """
        if not self._enabled or not self._weather_api_key:
            return None

        params = urllib.parse.urlencode({
            "q": city,
            "appid": self._weather_api_key,
            "units": "metric",
            "lang": "de",
        })
        url = f"https://api.openweathermap.org/data/2.5/weather?{params}"
        try:
            data = self._get_json(url)
            if data:
                desc = data["weather"][0]["description"]
                temp = data["main"]["temp"]
                return f"{city}: {desc}, {temp:.1f}°C"
        except Exception as exc:
            logger.error("Wetter-Anfrage fehlgeschlagen: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Generische HTTP-Helfer
    # ------------------------------------------------------------------

    def _get_json(self, url: str) -> Optional[Dict]:
        """Führt eine GET-Anfrage aus und gibt JSON zurück."""
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            logger.error("HTTP GET fehlgeschlagen: %s", exc)
            return None

    def _post_json(
        self,
        url: str,
        data: Dict,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict]:
        """Führt eine POST-Anfrage mit JSON-Body aus."""
        body = json.dumps(data).encode()
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(
            url, data=body, headers=req_headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            logger.error("HTTP POST fehlgeschlagen: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Verfügbarkeit
    # ------------------------------------------------------------------

    @property
    def llm_available(self) -> bool:
        return bool(self._llm_endpoint and self._llm_api_key and self._enabled)

    @property
    def weather_available(self) -> bool:
        return bool(self._weather_api_key and self._enabled)
