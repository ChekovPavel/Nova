"""Tests for nova.database.db_manager - DatabaseManager."""

from __future__ import annotations


class TestDatabaseManagerInit:
    """Schema creation and connection."""

    def test_creates_database_file(self, tmp_db):
        from nova.database.db_manager import DatabaseManager

        mgr = DatabaseManager(tmp_db)
        mgr.close()

        import os

        assert os.path.exists(tmp_db)

    def test_schema_version_stored(self, db_manager):
        row = db_manager.fetchone("SELECT value FROM meta WHERE key = 'schema_version'")
        assert row is not None

    def test_tables_created(self, db_manager):
        tables = {
            r["name"]
            for r in db_manager.fetchall(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for expected in ("meta", "memories", "persons", "personality_traits"):
            assert expected in tables, f"Table {expected!r} missing"


class TestInsertFetchall:
    """Basic CRUD through the convenience helpers."""

    def test_insert_and_fetchall(self, db_manager):
        mid = db_manager.insert(
            "memories",
            {
                "content": "test memory",
                "category": "general",
                "importance": 0.7,
                "tags": "[]",
                "created_at": "2024-01-01T00:00:00",
            },
        )
        assert mid > 0

        rows = db_manager.fetchall("SELECT * FROM memories WHERE id = ?", (mid,))
        assert len(rows) == 1
        assert rows[0]["content"] == "test memory"

    def test_fetchone_returns_none_for_missing(self, db_manager):
        row = db_manager.fetchone("SELECT * FROM memories WHERE id = ?", (999999,))
        assert row is None


class TestJsonHelpers:
    """to_json / from_json round-trip."""

    def test_round_trip(self, db_manager):
        data = {"key": "value", "list": [1, 2, 3]}
        encoded = db_manager.to_json(data)
        decoded = db_manager.from_json(encoded)
        assert decoded == data

    def test_from_json_invalid(self, db_manager):
        result = db_manager.from_json("not valid json")
        # Should return the raw string or an empty structure, not raise
        assert result is not None
