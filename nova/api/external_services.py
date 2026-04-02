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
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # Sekunden
_MAX_RETRIES = 3  # Standardanzahl Wiederholungsversuche
_BACKOFF_BASE = 2  # Basis für exponentielles Backoff (Sekunden)


class ExternalServices:
    """
    Bündelt externe API-Aufrufe.

    Alle Methoden kehren im Fehlerfall mit None / Fallback zurück.
    Es werden keine Secrets in Logs geschrieben.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._llm_endpoint: str | None = cfg.get("llm_endpoint")
        self._llm_api_key: str | None = cfg.get("llm_api_key")
        self._llm_model: str = cfg.get("llm_model", "gpt-3.5-turbo")
        self._weather_api_key: str | None = cfg.get("weather_api_key")
        self._calendar_endpoint: str | None = cfg.get("calendar_endpoint")
        self._calendar_api_key: str | None = cfg.get("calendar_api_key")
        self._enabled: bool = cfg.get("enabled", True)

    # ------------------------------------------------------------------
    # LLM-Vervollständigung
    # ------------------------------------------------------------------

    def complete(
        self,
        user_input: str,
        context: dict | None = None,
        system_prompt: str = (
            "Du bist Nova, ein freundlicher, empathischer persönlicher "
            "KI-Assistent. Antworte hilfreich, ehrlich und warmherzig."
        ),
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str | None:
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

    def get_weather(self, city: str) -> str | None:
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

    def _get_json(
        self, url: str, max_retries: int = _MAX_RETRIES,
    ) -> dict | None:
        """Führt eine GET-Anfrage aus und gibt JSON zurück (mit Retry)."""
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.URLError as exc:
                if attempt < max_retries - 1:
                    wait = _BACKOFF_BASE ** attempt
                    logger.warning(
                        "HTTP GET Versuch %d/%d fehlgeschlagen, "
                        "erneuter Versuch in %ds: %s",
                        attempt + 1, max_retries, wait, exc,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "HTTP GET fehlgeschlagen nach %d Versuchen: %s",
                        max_retries, exc,
                    )
        return None

    def _post_json(
        self,
        url: str,
        data: dict,
        headers: dict[str, str] | None = None,
        max_retries: int = _MAX_RETRIES,
    ) -> dict | None:
        """Führt eine POST-Anfrage mit JSON-Body aus (mit Retry)."""
        body = json.dumps(data).encode()
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        for attempt in range(max_retries):
            req = urllib.request.Request(
                url, data=body, headers=req_headers, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.URLError as exc:
                if attempt < max_retries - 1:
                    wait = _BACKOFF_BASE ** attempt
                    logger.warning(
                        "HTTP POST Versuch %d/%d fehlgeschlagen, "
                        "erneuter Versuch in %ds: %s",
                        attempt + 1, max_retries, wait, exc,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "HTTP POST fehlgeschlagen nach %d Versuchen: %s",
                        max_retries, exc,
                    )
        return None

    # ------------------------------------------------------------------
    # Kalender-Integration (Stub – Google Calendar / iCal)
    # ------------------------------------------------------------------

    def get_calendar_events(
        self,
        date_str: str | None = None,
        calendar_url: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """
        Ruft Kalendereinträge ab.

        Aktuell ein Stub – wird erweitert, sobald eine Calendar-API
        konfiguriert ist (``calendar_endpoint`` + ``calendar_api_key``
        in der Konfiguration).

        Args:
            date_str:     Datum im Format 'YYYY-MM-DD' (optional).
            calendar_url: Direkte iCal-URL (optional).

        Returns:
            Liste von Ereignis-Dicts oder None, wenn kein Dienst konfiguriert.
        """
        if not self._enabled:
            return None
        calendar_endpoint = getattr(self, "_calendar_endpoint", None)
        if not calendar_endpoint and not calendar_url:
            logger.info("Keine Kalender-API konfiguriert (calendar_endpoint fehlt).")
            return None
        url = calendar_url or calendar_endpoint
        try:
            params = urllib.parse.urlencode({"date": date_str} if date_str else {})
            full_url = f"{url}?{params}" if params else url
            data = self._get_json(full_url)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("items") or data.get("events") or []
        except Exception as exc:
            logger.error("Kalender-Anfrage fehlgeschlagen: %s", exc)
        return None

    def create_calendar_event(
        self,
        title: str,
        start: str,
        end: str,
        description: str = "",
        calendar_url: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Erstellt einen Kalendereintrag.

        Aktuell ein Stub – sendet eine POST-Anfrage, falls
        ``calendar_endpoint`` konfiguriert ist.

        Args:
            title:        Titel des Termins.
            start:        Startzeit (ISO-8601).
            end:          Endzeit (ISO-8601).
            description:  Optionale Beschreibung.
            calendar_url: Direkte API-URL (optional).

        Returns:
            Erstelltes Ereignis-Dict oder None.
        """
        if not self._enabled:
            return None
        calendar_endpoint = getattr(self, "_calendar_endpoint", None)
        url = calendar_url or calendar_endpoint
        if not url:
            logger.info("Keine Kalender-API konfiguriert – Termin nicht erstellt.")
            return None
        payload = {
            "summary": title,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
            "description": description,
        }
        try:
            headers = {}
            calendar_key = getattr(self, "_calendar_api_key", None)
            if calendar_key:
                headers["Authorization"] = f"Bearer {calendar_key}"
            return self._post_json(url, payload, headers=headers or None)
        except Exception as exc:
            logger.error("Kalender-Ereignis erstellen fehlgeschlagen: %s", exc)
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

    @property
    def calendar_available(self) -> bool:
        return bool(self._calendar_endpoint and self._enabled)
