import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

LABEL_NAME_MAX_LENGTH = 50

LabelColor = Literal["gray", "red", "orange", "amber", "green", "teal", "blue", "violet", "pink"]
_NON_ALNUM_RUN = re.compile(r"[\W_]+")

DisplayName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=LABEL_NAME_MAX_LENGTH)
]


def normalize_label_name(raw: str) -> str:
    """Canonical label name: lowercase, every run of non-alphanumerics (spaces, hyphens, punctuation,
    underscores) becomes one "_", no leading/trailing "_". "Credit Card-Bill!" -> "credit_card_bill".
    Letters and digits of any script are kept. Labels are globally unique on this form."""
    return _NON_ALNUM_RUN.sub("_", raw.lower()).strip("_")


class LabelCreate(BaseModel):
    """The normalised `name` is derived from the display name and can never change."""

    display_name: DisplayName
    color: LabelColor = "gray"

    @field_validator("display_name")
    @classmethod
    def has_normal_form(cls, value: str) -> str:
        if not normalize_label_name(value):
            raise ValueError("must contain at least one letter or digit")
        return value

    @property
    def name(self) -> str:
        return normalize_label_name(self.display_name)


class LabelUpdate(BaseModel):
    """Partial update of the display name and/or colour; the normalised name never changes."""

    model_config = ConfigDict(extra="forbid")

    display_name: DisplayName | None = None
    color: LabelColor | None = None

    @field_validator("display_name", "color")
    @classmethod
    def not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("cannot be null")
        return value


class LabelFilterRef(BaseModel):
    id: uuid.UUID
    name: str
    status: str


class LabelProcessorRef(BaseModel):
    id: uuid.UUID
    name: str
    status: str


class LabelRead(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    color: LabelColor
    email_count: int
    # Filters that write this label; a label can only be deleted when there are none.
    filters: list[LabelFilterRef]
    # Processors that run on this label; they block deleting it too.
    processors: list[LabelProcessorRef]
    # A built-in default: editable, but it can't be deleted.
    is_default: bool
    created_at: datetime
