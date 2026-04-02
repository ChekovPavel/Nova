"""Tests for nova.memory - ShortTermMemory and LongTermMemory."""

from __future__ import annotations

# ── ShortTermMemory ──────────────────────────────────────────────────────────


class TestSTMBasic:
    """ShortTermMemory add/get operations."""

    def test_add_and_get_recent(self, stm):
        stm.add("Nachricht eins")
        stm.add("Nachricht zwei")
        recent = stm.get_recent(n=5)
        assert len(recent) == 2

    def test_add_message(self, stm):
        entry = stm.add_message("user", "Hallo Nova")
        assert entry is not None
        msgs = stm.get_messages(n=5)
        assert any(m["text"] == "Hallo Nova" for m in msgs)

    def test_capacity_limit(self):
        from nova.memory.stm import ShortTermMemory

        small = ShortTermMemory(capacity=3)
        for i in range(5):
            small.add(f"msg-{i}")
        assert len(small) <= 3

    def test_clear(self, stm):
        stm.add("etwas")
        stm.clear()
        assert stm.is_empty

    def test_search(self, stm):
        stm.add("Python Programmierung")
        stm.add("Java Entwicklung")
        results = stm.search("Python")
        assert len(results) >= 1

    def test_summary_returns_dict(self, stm):
        assert isinstance(stm.summary(), dict)


# ── LongTermMemory ───────────────────────────────────────────────────────────


class TestLTMStore:
    """LongTermMemory store and recall."""

    def test_store_returns_id(self, ltm):
        mid = ltm.store("Eine wichtige Erinnerung", category="fact", importance=0.8)
        assert isinstance(mid, int)
        assert mid > 0

    def test_recall_by_query(self, ltm):
        ltm.store("Python ist eine Programmiersprache", category="fact")
        results = ltm.recall(query="Python")
        assert len(results) >= 1

    def test_recall_by_category(self, ltm):
        ltm.store("Termin am Montag", category="event")
        ltm.store("Fakt über Welt", category="fact")
        events = ltm.recall(category="event")
        assert all(r["category"] == "event" for r in events)

    def test_recall_by_id(self, ltm):
        mid = ltm.store("Einzigartig", category="general")
        mem = ltm.recall_by_id(mid)
        assert mem is not None
        assert "Einzigartig" in mem["content"]

    def test_forget(self, ltm):
        mid = ltm.store("Vergiss mich", category="general")
        assert ltm.forget(mid) is True
        assert ltm.recall_by_id(mid) is None

    def test_update_importance(self, ltm):
        mid = ltm.store("Neutral", category="general", importance=0.5)
        ltm.update_importance(mid, 0.95)
        mem = ltm.recall_by_id(mid)
        assert mem["importance"] >= 0.9

    def test_encrypted_store_and_recall(self, ltm):
        mid = ltm.store("Geheim!", category="general", encrypt=True)
        mem = ltm.recall_by_id(mid)
        assert mem is not None
        assert "Geheim!" in mem["content"]

    def test_stats_returns_dict(self, ltm):
        s = ltm.stats()
        assert isinstance(s, dict)

    def test_valid_categories(self, ltm):
        for cat in ("fact", "event", "person", "emotion", "general"):
            mid = ltm.store(f"test-{cat}", category=cat)
            assert mid > 0
