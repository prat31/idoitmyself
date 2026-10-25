import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.filters.rule import Rule
from app.models.filter import FilterStatus
from app.models.inbox import InboxProvider

FilterName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


def _blank_to_none(value: str | None) -> str | None:
    return value or None


class FilterScope(BaseModel):
    """Where a filter applies: every inbox of `mailbox_types` (including ones connected later) plus the
    inboxes in `inbox_ids`. Types may be mixed. At least one entry is required."""

    model_config = ConfigDict(extra="forbid")

    mailbox_types: list[InboxProvider] = Field(default_factory=list)
    inbox_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def not_empty(self) -> "FilterScope":
        self.mailbox_types = list(dict.fromkeys(self.mailbox_types))
        self.inbox_ids = list(dict.fromkeys(self.inbox_ids))
        if not self.mailbox_types and not self.inbox_ids:
            raise ValueError("Choose at least one mailbox type or inbox")
        return self


class FilterCreate(BaseModel):
    name: FilterName
    description: Description | None = None
    scope: FilterScope
    label_id: uuid.UUID
    rule: Rule
    status: FilterStatus = FilterStatus.ACTIVE  # live once created

    _blank_description = field_validator("description")(_blank_to_none)


class FilterUpdate(BaseModel):
    """Partial update. Edits apply to emails scanned from now on; labels already applied stay. A new
    scope or rule is re-checked: the rule may only use fields every covered mailbox type has."""

    model_config = ConfigDict(extra="forbid")

    name: FilterName | None = None
    description: Description | None = None
    scope: FilterScope | None = None
    label_id: uuid.UUID | None = None
    rule: Rule | None = None
    status: FilterStatus | None = None

    _blank_description = field_validator("description")(_blank_to_none)

    @field_validator("name", "scope", "label_id", "rule", "status")
    @classmethod
    def not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("cannot be null")
        return value


class FilterLabelRef(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    color: str


class ScopeInbox(BaseModel):
    id: uuid.UUID
    name: str
    email_address: str
    provider: InboxProvider


class FilterScopeRead(BaseModel):
    mailbox_types: list[InboxProvider]
    inboxes: list[ScopeInbox]


class FilterRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    scope: FilterScopeRead
    label: FilterLabelRef
    rule: Rule
    status: FilterStatus
    status_changed_at: datetime
    # Emails this filter labelled (it can share a label with other filters).
    emails_labelled: int
    last_matched_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OperatorRead(BaseModel):
    key: str
    label: str
    takes_value: bool


class FieldOption(BaseModel):
    value: str
    label: str


class FieldRead(BaseModel):
    key: str
    label: str
    type: str
    description: str
    mailbox_types: list[InboxProvider] | None  # null: every mailbox type
    options: list[FieldOption]
    argument_label: str | None


class FieldCatalogue(BaseModel):
    mailbox_types: list[InboxProvider]
    fields: list[FieldRead]
    operators: dict[str, list[OperatorRead]]  # by field type
