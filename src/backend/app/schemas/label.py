import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, field_validator

LabelColor = Literal["gray", "red", "orange", "amber", "green", "teal", "blue", "violet", "pink"]

FilterCondition = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
# Jev's P(yes) must reach this for a run to apply the label.
MatchThreshold = Annotated[float, Field(gt=0, lt=1)]

LABEL_NAME_MAX_LENGTH = 50
_NON_ALNUM_RUN = re.compile(r"[\W_]+")


def normalize_label_name(raw: str) -> str:
    """Canonical label name: lowercase, every run of non-alphanumerics (spaces, hyphens, punctuation,
    underscores) becomes one "_", no leading/trailing "_". "Credit Card-Bill!" -> "credit_card_bill".
    Letters and digits of any script are kept. Labels are globally unique on this form."""
    return _NON_ALNUM_RUN.sub("_", raw.lower()).strip("_")


def _validate_label_name(raw: str) -> str:
    name = normalize_label_name(raw)
    if not name:
        raise ValueError("must contain at least one letter or digit")
    if len(name) > LABEL_NAME_MAX_LENGTH:
        raise ValueError(f"must be at most {LABEL_NAME_MAX_LENGTH} characters")
    return name


LabelName = Annotated[str, AfterValidator(_validate_label_name)]


def _blank_to_none(value: str | None) -> str | None:
    return value or None


class LabelCreate(BaseModel):
    name: LabelName
    description: Description | None = None
    color: LabelColor = "gray"
    filter_condition: FilterCondition | None = None
    match_threshold: MatchThreshold = 0.5

    _blank_description = field_validator("description")(_blank_to_none)
    _blank_filter_condition = field_validator("filter_condition")(_blank_to_none)


class LabelUpdate(BaseModel):
    """Partial update. Description, colour, filter condition and match threshold are editable; the
    name is not, and any other field (e.g. name) is rejected. Omitted fields are unchanged; null
    clears description or filter condition."""

    model_config = ConfigDict(extra="forbid")

    description: Description | None = None
    color: LabelColor | None = None
    filter_condition: FilterCondition | None = None
    match_threshold: MatchThreshold | None = None

    _blank_description = field_validator("description")(_blank_to_none)
    _blank_filter_condition = field_validator("filter_condition")(_blank_to_none)

    @field_validator("color", "match_threshold")
    @classmethod
    def not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("cannot be null")
        return value


class LabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    color: LabelColor
    filter_condition: str | None
    match_threshold: float
    email_count: int
    created_at: datetime
