import pytest
from pydantic import ValidationError

from app.models.label import LABEL_COLORS
from app.schemas.label import LabelColor, LabelCreate, LabelUpdate, normalize_label_name


def test_defaults_and_trimming():
    label = LabelCreate(name="  Receipts ", description="   ")
    assert label.name == "receipts"
    assert label.description is None
    assert label.color == "gray"


def test_unknown_color_rejected():
    with pytest.raises(ValidationError):
        LabelCreate(name="x", color="neon")


def test_schema_palette_matches_model_palette():
    assert set(LabelColor.__args__) == set(LABEL_COLORS)


def test_filter_condition_optional_and_blank_becomes_none():
    assert LabelCreate(name="x").filter_condition is None
    assert LabelCreate(name="x", filter_condition="   ").filter_condition is None
    assert (
        LabelCreate(name="x", filter_condition=" Receipts from shops ").filter_condition
        == "Receipts from shops"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Credit Card Bill", "credit_card_bill"),
        ("  CreditCardBill ", "creditcardbill"),
        ("Credit-Card__Bill!!", "credit_card_bill"),
        ("__Travel / Trips__", "travel_trips"),
        ("Café Reçus 2026", "café_reçus_2026"),
    ],
)
def test_name_is_normalized(raw, expected):
    assert normalize_label_name(raw) == expected
    assert LabelCreate(name=raw).name == expected


@pytest.mark.parametrize("raw", ["", "   ", "!!!", "_-_", "a" * 51])
def test_invalid_names_rejected(raw):
    with pytest.raises(ValidationError):
        LabelCreate(name=raw)


def test_update_is_partial_and_rejects_name():
    update = LabelUpdate(description="  ", color="blue")
    assert update.model_fields_set == {"description", "color"}
    assert update.description is None
    assert LabelUpdate(filter_condition="  ").filter_condition is None
    with pytest.raises(ValidationError):
        LabelUpdate(filter_condition="x", name="renamed")
    with pytest.raises(ValidationError):
        LabelUpdate(color=None)


def test_filter_condition_length_limit():
    with pytest.raises(ValidationError):
        LabelCreate(name="x", filter_condition="a" * 2001)
