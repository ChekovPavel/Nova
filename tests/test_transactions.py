"""Tests for transaction support in nova.database.db_manager."""

from __future__ import annotations

import pytest


class TestTransactionCommit:
    """Transactions should auto-commit on success."""

    def test_transaction_commits_on_success(self, db_manager):
        with db_manager.transaction():
            db_manager._conn.execute(
                "INSERT INTO personality_traits(trait, value) VALUES(?, ?)",
                ("test_trait", 0.5),
            )

        row = db_manager.fetchone(
            "SELECT value FROM personality_traits WHERE trait = ?",
            ("test_trait",),
        )
        assert row is not None
        assert row["value"] == 0.5


class TestTransactionRollback:
    """Transactions should auto-rollback on exception."""

    def test_transaction_rolls_back_on_error(self, db_manager):
        try:
            with db_manager.transaction():
                db_manager._conn.execute(
                    "INSERT INTO personality_traits(trait, value) VALUES(?, ?)",
                    ("rollback_test", 0.9),
                )
                raise ValueError("Simulated error")
        except ValueError:
            pass

        row = db_manager.fetchone(
            "SELECT value FROM personality_traits WHERE trait = ?",
            ("rollback_test",),
        )
        assert row is None, "Row should have been rolled back"

    def test_transaction_reraises_exception(self, db_manager):
        with pytest.raises(RuntimeError, match="boom"), db_manager.transaction():
            raise RuntimeError("boom")


class TestTransactionMultipleOps:
    """Multiple operations in a single transaction."""

    def test_multiple_inserts_committed(self, db_manager):
        with db_manager.transaction():
            db_manager._conn.execute(
                "INSERT INTO personality_traits(trait, value) VALUES(?, ?)",
                ("multi_a", 0.1),
            )
            db_manager._conn.execute(
                "INSERT INTO personality_traits(trait, value) VALUES(?, ?)",
                ("multi_b", 0.2),
            )

        a = db_manager.fetchone(
            "SELECT value FROM personality_traits WHERE trait = ?",
            ("multi_a",),
        )
        b = db_manager.fetchone(
            "SELECT value FROM personality_traits WHERE trait = ?",
            ("multi_b",),
        )
        assert a is not None and b is not None

    def test_partial_failure_rolls_back_all(self, db_manager):
        try:
            with db_manager.transaction():
                db_manager._conn.execute(
                    "INSERT INTO personality_traits(trait, value) VALUES(?, ?)",
                    ("partial_a", 0.1),
                )
                # Second insert will fail - trait is PRIMARY KEY so duplicate
                db_manager._conn.execute(
                    "INSERT INTO personality_traits(trait, value) VALUES(?, ?)",
                    ("partial_a", 0.2),  # duplicate key
                )
        except Exception:
            pass

        row = db_manager.fetchone(
            "SELECT value FROM personality_traits WHERE trait = ?",
            ("partial_a",),
        )
        assert row is None, "Both inserts should have been rolled back"
