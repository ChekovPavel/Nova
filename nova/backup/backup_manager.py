"""
Kapitel 26 - Backup-System

Erstellt automatisch Backups der SQLite-Datenbank (nova_data.db).
Privaten Personendaten und Erinnerungen sind damit vor Datenverlust
geschützt.

Features:
- Zeitgesteuerte Backups (stündlich / täglich)
- Rotierendes Archiv (maximal N Backups behalten)
- Komprimierung (gzip)
- Integritätsprüfung der Backup-Datei
- Wiederherstellung einzelner Backups
- Backup-Verzeichnis außerhalb des Git-Repos empfohlen
"""

from __future__ import annotations

import gzip
import hashlib
import logging
import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_BACKUP_DIR = os.path.expanduser("~/nova_backups")
_DEFAULT_MAX_BACKUPS = 30  # maximale Anzahl gespeicherter Backups
_DEFAULT_INTERVAL_SEC = 3600  # Backup-Intervall: 1 Stunde
_DEFAULT_DAILY_INTERVAL = 86400  # Täglich vollständiges Backup


class BackupManager:
    """
    Verwaltet automatische Backups der Nova-Datenbank.

    Backup-Strategie:
    - Stündliche Backups (komprimiert, rotierend)
    - Täglich vollständiges Backup in separatem Ordner
    - Integritätsprüfung via SHA256-Checksum
    - Automatischer Hintergrund-Thread
    """

    def __init__(
        self,
        db_path: str,
        backup_dir: str = _DEFAULT_BACKUP_DIR,
        max_backups: int = _DEFAULT_MAX_BACKUPS,
        interval_sec: float = _DEFAULT_INTERVAL_SEC,
        enabled: bool = True,
    ) -> None:
        self.db_path = os.path.abspath(db_path)
        self.backup_dir = os.path.abspath(os.path.expanduser(backup_dir))
        self.daily_dir = os.path.join(self.backup_dir, "daily")
        self.max_backups = max_backups
        self.interval_sec = interval_sec
        self.enabled = enabled

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_backup: float | None = None
        self._last_daily: float | None = None

        if enabled:
            os.makedirs(self.backup_dir, exist_ok=True)
            os.makedirs(self.daily_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Automatischer Hintergrund-Thread
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Startet den Backup-Hintergrund-Thread."""
        if not self.enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._backup_loop,
            daemon=True,
            name="nova-backup",
        )
        self._thread.start()
        logger.info(
            "Backup-Thread gestartet (Intervall: %ds, Ziel: %s).",
            self.interval_sec,
            self.backup_dir,
        )

    def stop(self) -> None:
        """Stoppt den Backup-Thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _backup_loop(self) -> None:
        """Hauptschleife des Backup-Threads."""
        # Erstes Backup direkt beim Start
        self._do_backup(daily=True)

        while not self._stop_event.wait(timeout=min(self.interval_sec, 300)):
            now = time.monotonic()

            # Stündliches Backup
            if (
                self._last_backup is None
                or (now - self._last_backup) >= self.interval_sec
            ):
                self._do_backup(daily=False)

            # Tägliches Backup
            if (
                self._last_daily is None
                or (now - self._last_daily) >= _DEFAULT_DAILY_INTERVAL
            ):
                self._do_backup(daily=True)

    # ------------------------------------------------------------------
    # Backup erstellen
    # ------------------------------------------------------------------

    def backup_now(self, label: str = "") -> str | None:
        """
        Erstellt sofort ein Backup.

        Args:
            label: Optionaler Bezeichner im Dateinamen.

        Returns:
            Pfad zur Backup-Datei oder None bei Fehler.
        """
        return self._do_backup(daily=False, label=label)

    def _do_backup(self, daily: bool = False, label: str = "") -> str | None:
        """Interne Backup-Methode."""
        if not os.path.exists(self.db_path):
            logger.warning("Datenbank nicht gefunden: %s", self.db_path)
            return None

        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d_%H%M%S")
        suffix = f"_{label}" if label else ""
        fname = f"nova_backup_{ts}{suffix}.db.gz"
        target_dir = self.daily_dir if daily else self.backup_dir
        dest_path = os.path.join(target_dir, fname)

        try:
            # SQLite Online-Backup (sicher auch bei laufender DB)
            backup_raw = dest_path.replace(".gz", "")
            self._sqlite_backup(self.db_path, backup_raw)

            # Komprimieren
            with (
                open(backup_raw, "rb") as f_in,
                gzip.open(dest_path, "wb", compresslevel=6) as f_out,
            ):
                shutil.copyfileobj(f_in, f_out)
            os.unlink(backup_raw)

            # Checksum speichern
            checksum = self._sha256(dest_path)
            checksum_file = dest_path + ".sha256"
            with open(checksum_file, "w") as f:
                f.write(f"{checksum}  {os.path.basename(dest_path)}\n")

            size_kb = os.path.getsize(dest_path) / 1024
            logger.info(
                "Backup erstellt: %s (%.1f KB, SHA256: %s…)",
                dest_path,
                size_kb,
                checksum[:12],
            )

            # Rotation: alte Backups löschen
            if not daily:
                self._rotate(self.backup_dir)

            now_mono = time.monotonic()
            if daily:
                self._last_daily = now_mono
            else:
                self._last_backup = now_mono

            return dest_path

        except Exception as exc:
            logger.error("Backup fehlgeschlagen: %s", exc)
            return None

    # ------------------------------------------------------------------
    # SQLite-Online-Backup
    # ------------------------------------------------------------------

    @staticmethod
    def _sqlite_backup(src_path: str, dest_path: str) -> None:
        """
        Erstellt ein konsistentes SQLite-Backup während die DB läuft.
        Nutzt die sqlite3.Connection.backup()-API.
        """
        src_conn = sqlite3.connect(src_path)
        dst_conn = sqlite3.connect(dest_path)
        try:
            # pages=100: Anzahl der pro Iteration kopierten DB-Seiten.
            # Kleinere Werte → kürzere DB-Sperren pro Iteration, aber mehr
            # Iterationen; -1 kopiert alles in einem Schritt.
            src_conn.backup(dst_conn, pages=100)
        finally:
            src_conn.close()
            dst_conn.close()

    # ------------------------------------------------------------------
    # Rotation
    # ------------------------------------------------------------------

    def _rotate(self, directory: str) -> None:
        """Löscht älteste Backups, wenn max_backups überschritten."""
        pattern = "nova_backup_*.db.gz"
        backups = sorted(Path(directory).glob(pattern))
        while len(backups) > self.max_backups:
            oldest = backups.pop(0)
            oldest.unlink(missing_ok=True)
            checksum = Path(str(oldest) + ".sha256")
            checksum.unlink(missing_ok=True)
            logger.debug("Altes Backup gelöscht: %s", oldest.name)

    # ------------------------------------------------------------------
    # Wiederherstellung
    # ------------------------------------------------------------------

    def restore(self, backup_path: str, target_path: str | None = None) -> bool:
        """
        Stellt ein Backup wieder her.

        Args:
            backup_path: Pfad zur .db.gz-Backup-Datei.
            target_path: Ziel-DB-Pfad (Standard: originale db_path).

        Returns:
            True bei Erfolg.
        """
        target = target_path or self.db_path

        # Integritätsprüfung
        checksum_file = backup_path + ".sha256"
        if os.path.exists(checksum_file):
            with open(checksum_file) as f:
                stored = f.read().split()[0]
            actual = self._sha256(backup_path)
            if stored != actual:
                logger.error(
                    "Backup-Integritätsprüfung fehlgeschlagen! "
                    "Erwartet: %s, Gefunden: %s",
                    stored,
                    actual,
                )
                return False

        # Sicherungskopie der aktuellen DB
        if os.path.exists(target):
            backup_of_current = target + ".before_restore"
            shutil.copy2(target, backup_of_current)
            logger.info("Aktuelle DB gesichert: %s", backup_of_current)

        # Wiederherstellen
        try:
            with gzip.open(backup_path, "rb") as f_in, open(target, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            logger.info("Backup wiederhergestellt: %s → %s", backup_path, target)
            return True
        except Exception as exc:
            logger.error("Wiederherstellung fehlgeschlagen: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_backups(self, daily: bool = False) -> list[dict]:
        """
        Listet verfügbare Backups auf.

        Returns:
            Liste von Dicts mit path, size_kb, timestamp.
        """
        directory = self.daily_dir if daily else self.backup_dir
        backups = []
        for f in sorted(Path(directory).glob("nova_backup_*.db.gz"), reverse=True):
            stat = f.stat()
            backups.append(
                {
                    "path": str(f),
                    "filename": f.name,
                    "size_kb": stat.st_size / 1024,
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
        return backups

    def latest_backup(self) -> str | None:
        """Gibt den Pfad zum neuesten Backup zurück."""
        backups = self.list_backups()
        return backups[0]["path"] if backups else None

    # ------------------------------------------------------------------
    # Helfer
    # ------------------------------------------------------------------

    @staticmethod
    def _sha256(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Gibt eine Übersicht über den Backup-Status zurück."""
        backups = self.list_backups()
        daily_backups = self.list_backups(daily=True)
        return {
            "enabled": self.enabled,
            "db_path": self.db_path,
            "backup_dir": self.backup_dir,
            "total_backups": len(backups),
            "total_daily_backups": len(daily_backups),
            "latest": backups[0]["filename"] if backups else None,
            "latest_daily": daily_backups[0]["filename"] if daily_backups else None,
        }
