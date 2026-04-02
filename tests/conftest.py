"""Shared test fixtures for Nova test suite."""
from __future__ import annotations

import pytest


@pytest.fixture()
def tmp_db(tmp_path):
    """Provide a temporary database path that is cleaned up after the test."""
    return str(tmp_path / "test_nova.db")


@pytest.fixture()
def db_manager(tmp_db):
    """Provide a fresh DatabaseManager instance backed by a temp file."""
    from nova.database.db_manager import DatabaseManager

    mgr = DatabaseManager(tmp_db)
    yield mgr
    mgr.close()


@pytest.fixture()
def security():
    """Provide a SecurityManager with a deterministic test key."""
    from nova.security.encryption import SecurityManager

    return SecurityManager(secret_key="test-secret-key-for-unit-tests")


@pytest.fixture()
def safety():
    """Provide a SocialSafetyLayer instance."""
    from nova.safety.social_safety import SocialSafetyLayer

    return SocialSafetyLayer()


@pytest.fixture()
def nlp():
    """Provide an NLPProcessor instance."""
    from nova.nlp.processor import NLPProcessor

    return NLPProcessor()


@pytest.fixture()
def personality(db_manager):
    """Provide a Personality instance backed by the temp database."""
    from nova.personality.personality import Personality

    return Personality(db_manager)


@pytest.fixture()
def emotion(personality):
    """Provide an EmotionEngine instance."""
    from nova.personality.emotion import EmotionEngine

    return EmotionEngine(personality)


@pytest.fixture()
def stm():
    """Provide a ShortTermMemory with default capacity."""
    from nova.memory.stm import ShortTermMemory

    return ShortTermMemory(capacity=20)


@pytest.fixture()
def ltm(db_manager, security):
    """Provide a LongTermMemory backed by the temp database."""
    from nova.memory.ltm import LongTermMemory

    return LongTermMemory(db_manager, security)


@pytest.fixture()
def relationships(db_manager):
    """Provide a RelationshipModel backed by the temp database."""
    from nova.relationships.relationship import RelationshipModel

    return RelationshipModel(db_manager)


@pytest.fixture()
def mode_manager(emotion):
    """Provide a ModeManager instance."""
    from nova.modes.mode_manager import ModeManager

    return ModeManager(emotion)


@pytest.fixture()
def profile_manager():
    """Provide a ProfileManager instance."""
    from nova.profiles.profile_manager import ProfileManager

    return ProfileManager(stm_capacity=20)
