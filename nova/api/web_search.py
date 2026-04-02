"""
Kapitel 16.6 - Online-Personensuche & allgemeine Websuche

Ermöglicht Nova, öffentlich verfügbare Informationen über Personen
oder Themen nachzuschlagen.

Quellen (in Priorität, kein API-Key erforderlich):
1. Wikipedia Deutsch (REST API)
2. Wikipedia Englisch (REST API)
3. DuckDuckGo Instant Answers (JSON API)

Datenschutz-Hinweis:
    Es werden ausschließlich öffentlich indexierte Daten genutzt.
    Die Suche wird NUR auf explizite Anfrage des Nutzers ausgeführt
    (kein automatisches stilles Profiling).
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_TIMEOUT = 8  # Sekunden
_DDG_URL = "https://api.duckduckgo.com/"
_WIKI_SUMMARY_DE = "https://de.wikipedia.org/api/rest_v1/page/summary/"
_WIKI_SUMMARY_EN = "https://en.wikipedia.org/api/rest_v1/page/summary/"
_USER_AGENT = "Nova-AI/1.0 (personal assistant; non-commercial)"


class WebSearch:
    """
    Sucht öffentlich zugängliche Informationen zu Personen und Themen.

    Alle Methoden kehren bei Netzwerkfehler mit None/leerem Dict zurück -
    Nova läuft auch ohne Internetzugang weiter.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    # ------------------------------------------------------------------
    # Personensuche
    # ------------------------------------------------------------------

    def search_person(self, name: str) -> dict[str, Any]:
        """
        Sucht Informationen über eine (öffentlich bekannte) Person online.

        Args:
            name: Name der Person.

        Returns:
            Dict mit Feldern: name, description, abstract, url, source.
            Nicht gefundene Felder sind None.
        """
        result: dict[str, Any] = {
            "name": name,
            "description": None,
            "abstract": None,
            "url": None,
            "source": None,
        }

        if not self._enabled:
            logger.debug("WebSearch deaktiviert.")
            return result

        # Priorität 1: Wikipedia Deutsch
        wiki = self._search_wikipedia(name, lang="de")
        if wiki:
            result.update(wiki)
            result["source"] = "wikipedia_de"
            logger.info("WebSearch: Person %r via Wikipedia (de) gefunden.", name)
            return result

        # Priorität 2: Wikipedia Englisch
        wiki = self._search_wikipedia(name, lang="en")
        if wiki:
            result.update(wiki)
            result["source"] = "wikipedia_en"
            logger.info("WebSearch: Person %r via Wikipedia (en) gefunden.", name)
            return result

        # Priorität 3: DuckDuckGo Instant Answers
        ddg = self._search_duckduckgo(name)
        if ddg:
            result.update(ddg)
            result["source"] = "duckduckgo"
            logger.info("WebSearch: Person %r via DuckDuckGo gefunden.", name)
            return result

        logger.info("WebSearch: Keine Ergebnisse für %r.", name)
        return result

    # ------------------------------------------------------------------
    # Themensuche
    # ------------------------------------------------------------------

    def search_topic(self, query: str) -> str | None:
        """
        Allgemeine Themensuche via DuckDuckGo Instant Answers.

        Args:
            query: Suchanfrage.

        Returns:
            Kurzer Antworttext oder None.
        """
        if not self._enabled:
            return None

        # Erst Wikipedia probieren
        wiki = self._search_wikipedia(query, lang="de")
        if wiki and wiki.get("abstract"):
            return wiki["abstract"]
        wiki = self._search_wikipedia(query, lang="en")
        if wiki and wiki.get("abstract"):
            return wiki["abstract"]

        # Dann DuckDuckGo
        ddg = self._search_duckduckgo(query)
        if ddg:
            return ddg.get("abstract") or ddg.get("description")

        return None

    # ------------------------------------------------------------------
    # Interne Suchmethoden
    # ------------------------------------------------------------------

    def _search_wikipedia(self, query: str, lang: str = "de") -> dict[str, Any] | None:
        """Ruft die Wikipedia-Zusammenfassung für einen Begriff ab."""
        base = _WIKI_SUMMARY_DE if lang == "de" else _WIKI_SUMMARY_EN
        encoded = urllib.parse.quote(query.replace(" ", "_"))
        url = f"{base}{encoded}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())

            # Disambiguationsseiten überspringen
            if data.get("type") in ("disambiguation", "no-extract"):
                return None

            abstract = data.get("extract", "").strip()
            if not abstract:
                return None

            return {
                "abstract": abstract[:600],
                "description": data.get("description"),
                "url": (data.get("content_urls", {}).get("desktop", {}).get("page")),
            }
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                logger.debug("Wikipedia (%s) HTTP-Fehler für %r: %s", lang, query, exc)
        except Exception as exc:
            logger.debug(
                "Wikipedia (%s) Anfrage fehlgeschlagen für %r: %s",
                lang,
                query,
                exc,
            )
        return None

    def _search_duckduckgo(self, query: str) -> dict[str, Any] | None:
        """Nutzt die DuckDuckGo Instant Answers JSON-API."""
        params = urllib.parse.urlencode(
            {
                "q": query,
                "format": "json",
                "no_redirect": "1",
                "no_html": "1",
                "skip_disambig": "1",
            }
        )
        url = f"{_DDG_URL}?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())

            abstract = data.get("AbstractText", "").strip()
            if not abstract:
                return None

            return {
                "abstract": abstract[:600],
                "description": data.get("Heading") or None,
                "url": data.get("AbstractURL") or None,
            }
        except Exception as exc:
            logger.debug("DuckDuckGo-Anfrage fehlgeschlagen: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Hilfsmethode: Ergebnis für Nova-Antwort formatieren
    # ------------------------------------------------------------------

    def format_result(self, result: dict[str, Any]) -> str:
        """
        Formatiert ein Suchergebnis als lesbaren Text für Novas Antwort.

        Args:
            result: Dict aus search_person() oder search_topic().

        Returns:
            Menschenlesbarer String.
        """
        name = result.get("name", "")
        abstract = result.get("abstract")
        description = result.get("description")
        url = result.get("url")
        source = result.get("source")

        if not abstract and not description:
            return (
                f"Ich konnte online leider keine Informationen "
                f'\u00fcber "{name}" finden.'
            )

        parts = []
        if description:
            parts.append(f"**{name}** - {description}")
        if abstract:
            parts.append(abstract)
        if url:
            parts.append(f"🔗 {url}")
        if source:
            source_label = {
                "wikipedia_de": "Wikipedia (Deutsch)",
                "wikipedia_en": "Wikipedia (Englisch)",
                "duckduckgo": "DuckDuckGo",
            }.get(source, source)
            parts.append(f"_(Quelle: {source_label})_")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Eigenschaften
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return self._enabled

    def __repr__(self) -> str:
        return f"<WebSearch enabled={self._enabled}>"
