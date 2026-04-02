"""Tests for nova.relationships.relationship – RelationshipModel & Person."""
from __future__ import annotations


class TestAddAndFind:
    """Person creation and lookup."""

    def test_add_person(self, relationships):
        person = relationships.add_person("Anna")
        assert person is not None
        assert person.to_dict()["name"] == "Anna"

    def test_find_by_name(self, relationships):
        relationships.add_person("Bob")
        found = relationships.find_by_name("Bob")
        assert found is not None

    def test_find_missing_returns_none(self, relationships):
        assert relationships.find_by_name("Nobody") is None

    def test_list_persons(self, relationships):
        relationships.add_person("Clara")
        relationships.add_person("David")
        persons = relationships.list_persons()
        names = [p.to_dict()["name"] for p in persons]
        assert "Clara" in names
        assert "David" in names


class TestTrustAndRelationship:
    """Trust level adjustments and relationship status."""

    def test_adjust_trust(self, relationships):
        person = relationships.add_person("Eve", trust_level=0.5)
        pid = person.to_dict()["id"]
        relationships.adjust_trust(pid, 0.2)
        updated = relationships.get_by_id(pid)
        assert updated.to_dict()["trust_level"] >= 0.6

    def test_relationship_status(self, relationships):
        person = relationships.add_person("Frank")
        assert person.relationship_status in (
            "stranger", "acquaintance", "crush", "dating",
            "partner", "ex", "colleague", "friend",
        )

    def test_set_relationship_status(self, relationships):
        person = relationships.add_person("Gina")
        person.set_relationship_status("friend")
        assert person.relationship_status == "friend"


class TestRemovePerson:
    """Person deletion."""

    def test_remove_existing(self, relationships):
        person = relationships.add_person("ToDelete")
        pid = person.to_dict()["id"]
        assert relationships.remove_person(pid) is True
        assert relationships.get_by_id(pid) is None


class TestTimeline:
    """Event timeline for a person."""

    def test_add_timeline_event(self, relationships):
        person = relationships.add_person("Hannah")
        pid = person.to_dict()["id"]
        eid = relationships.add_timeline_event(pid, "meeting", "Erstes Treffen")
        assert eid is not None

    def test_get_timeline(self, relationships):
        person = relationships.add_person("Ivan")
        pid = person.to_dict()["id"]
        relationships.add_timeline_event(pid, "call", "Telefonat")
        events = relationships.get_timeline(pid)
        assert len(events) >= 1


class TestDatingFeatures:
    """Dating-specific person features."""

    def test_add_interest(self, relationships):
        person = relationships.add_person("Julia")
        person.add_interest("Wandern")
        interests = person.get_interests()
        assert "Wandern" in interests

    def test_date_ideas(self, relationships):
        person = relationships.add_person("Kevin")
        person.set_date_idea("Picknick im Park")
        ideas = person.get_date_ideas()
        assert "Picknick im Park" in ideas

    def test_dating_info(self, relationships):
        person = relationships.add_person("Lisa")
        info = person.dating_info()
        assert isinstance(info, dict)
