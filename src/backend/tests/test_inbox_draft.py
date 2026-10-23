import pytest
from pydantic import ValidationError

from app.schemas.inbox import InboxDraft


def test_tags_are_trimmed_and_deduplicated_case_insensitively():
    draft = InboxDraft(name="  Personal ", tags=[" Work", "work", "Bills ", "BILLS"])
    assert draft.name == "Personal"
    assert draft.tags == ["Work", "Bills"]


def test_blank_notes_become_none():
    assert InboxDraft(name="x", notes="   ").notes is None


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_invalid_names_are_rejected(name):
    with pytest.raises(ValidationError):
        InboxDraft(name=name)


def test_too_many_tags_rejected():
    with pytest.raises(ValidationError):
        InboxDraft(name="x", tags=[f"t{i}" for i in range(21)])
