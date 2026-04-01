"""
Kapitel 18 – Datenbank & Persistenz

SQLite-basierter Datenbankmanager.  Alle Subsysteme schreiben und lesen
über diese Klasse, so dass das Datenbankschema an einer zentralen Stelle
verwaltet wird.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Thread-sicherer SQLite-Wrapper für Nova."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str = "nova_data.db") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._apply_schema()

    # ------------------------------------------------------------------
    # Verbindung
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _apply_schema(self) -> None:
        ddl_statements = [
            # Metadaten
            """CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""",
            # Langzeitgedächtnis
            """CREATE TABLE IF NOT EXISTS memories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category    TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                importance  REAL    DEFAULT 0.5,
                encrypted   INTEGER DEFAULT 0,
                created_at  TEXT    NOT NULL,
                accessed_at TEXT,
                access_count INTEGER DEFAULT 0,
                tags        TEXT    DEFAULT '[]'
            )""",
            # Beziehungen / Personen
            """CREATE TABLE IF NOT EXISTS persons (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                aliases     TEXT    DEFAULT '[]',
                profile     TEXT    DEFAULT '{}',
                trust_level REAL    DEFAULT 0.5,
                first_seen  TEXT    NOT NULL,
                last_seen   TEXT
            )""",
            # Persönlichkeits-Trait-Werte
            """CREATE TABLE IF NOT EXISTS personality_traits (
                trait TEXT PRIMARY KEY,
                value REAL NOT NULL
            )""",
            # Lerneinträge
            """CREATE TABLE IF NOT EXISTS learned_facts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                subject    TEXT NOT NULL,
                predicate  TEXT NOT NULL,
                obj        TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source     TEXT,
                created_at TEXT NOT NULL
            )""",
            # Ziele
            """CREATE TABLE IF NOT EXISTS goals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                description TEXT,
                priority    REAL DEFAULT 0.5,
                status      TEXT DEFAULT 'open',
                created_at  TEXT NOT NULL,
                updated_at  TEXT
            )""",
            # Konversationslog
            """CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                timestamp  TEXT NOT NULL,
                person_id  INTEGER REFERENCES persons(id)
            )""",
        ]
        with self._lock:
            cur = self._conn.cursor()
            for stmt in ddl_statements:
                cur.execute(stmt)
            # Schema-Version setzen
            cur.execute(
                "INSERT OR IGNORE INTO meta(key,value) VALUES(?,?)",
                ("schema_version", str(self.SCHEMA_VERSION)),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # CRUD-Helfer
    # ------------------------------------------------------------------

    def execute(
        self,
        sql: str,
        params: Tuple = (),
        commit: bool = False,
    ) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            if commit:
                self._conn.commit()
            return cur

    def fetchall(self, sql: str, params: Tuple = ()) -> List[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def fetchone(
        self, sql: str, params: Tuple = ()
    ) -> Optional[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchone()

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        with self._lock:
            cur = self._conn.execute(sql, tuple(data.values()))
            self._conn.commit()
            return cur.lastrowid

    def update(
        self,
        table: str,
        data: Dict[str, Any],
        where: str,
        where_params: Tuple = (),
    ) -> int:
        sets = ", ".join(f"{k}=?" for k in data.keys())
        sql = f"UPDATE {table} SET {sets} WHERE {where}"
        with self._lock:
            cur = self._conn.execute(
                sql, tuple(data.values()) + where_params
            )
            self._conn.commit()
            return cur.rowcount

    # ------------------------------------------------------------------
    # JSON-Helfer
    # ------------------------------------------------------------------

    @staticmethod
    def to_json(obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False)

    @staticmethod
    def from_json(text: str) -> Any:
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text
