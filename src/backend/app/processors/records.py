"""Datasets: typed tables that processors write records into, and dashboards query.

A dataset is a Record subclass. Its fields say what each column is for:

    class Statement(Record, dataset="cards.statements", time="statement_date"):
        bank: str = Dimension(title="Bank")              # group and filter by it
        statement_date: date = Time(title="Statement")   # when it happened (`time` picks the main one)
        total_due: Money = Measure(title="Total due")    # add it up
        note: str | None = Text(title="Note", default=None)  # shown, not grouped

Datasets are global: several kinds may write the same one (import the same class), and a dashboard can
mix datasets from different processors. `kind="event"` datasets only add up (bills, transactions);
`kind="snapshot"` ones describe the latest state of something per `key` (a card's limit, a holding)."""

import types
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Literal, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import PydanticUndefined


class _MoneyMarker:
    pass


# An amount of money (a Decimal; JSON as a string, so nothing is lost to floats).
Money = Annotated[Decimal, _MoneyMarker()]

FieldType = Literal["text", "number", "money", "date", "datetime", "bool"]


class FieldRole(StrEnum):
    DIMENSION = "dimension"  # group by and filter on it (bank, card, category)
    MEASURE = "measure"  # aggregate it (sum, average, ...)
    TIME = "time"  # a point in time
    TEXT = "text"  # shown in tables only (descriptions, notes)


def _field(role: FieldRole, default: Any, title: str, description: str | None) -> Any:
    return Field(default, title=title, description=description, json_schema_extra={"role": role.value})


def Dimension(default: Any = PydanticUndefined, *, title: str, description: str | None = None) -> Any:  # noqa: N802
    return _field(FieldRole.DIMENSION, default, title, description)


def Measure(default: Any = PydanticUndefined, *, title: str, description: str | None = None) -> Any:  # noqa: N802
    return _field(FieldRole.MEASURE, default, title, description)


def Time(default: Any = PydanticUndefined, *, title: str, description: str | None = None) -> Any:  # noqa: N802
    return _field(FieldRole.TIME, default, title, description)


def Text(default: Any = PydanticUndefined, *, title: str, description: str | None = None) -> Any:  # noqa: N802
    return _field(FieldRole.TEXT, default, title, description)


@dataclass(frozen=True)
class DatasetField:
    name: str
    title: str
    type: FieldType
    role: FieldRole
    description: str | None


@dataclass(frozen=True)
class Dataset:
    name: str
    title: str
    kind: Literal["event", "snapshot"]
    version: int
    time_field: str
    key_field: str | None
    fields: tuple[DatasetField, ...]
    model: type["Record"]

    def field(self, name: str) -> DatasetField | None:
        return next((f for f in self.fields if f.name == name), None)


# Every dataset, by name. Filled as Record subclasses are defined.
DATASETS: dict[str, Dataset] = {}


def _field_type(annotation: Any, metadata: list[Any]) -> FieldType:
    if any(isinstance(m, _MoneyMarker) for m in metadata):
        return "money"  # pydantic moves a top-level Annotated's metadata to the field
    if get_origin(annotation) in (Union, types.UnionType):
        annotation = next(a for a in get_args(annotation) if a is not type(None))
    if get_origin(annotation) is Annotated:
        base, *metadata = get_args(annotation)
        if any(isinstance(m, _MoneyMarker) for m in metadata):
            return "money"
        annotation = base
    if annotation is bool:
        return "bool"
    if annotation in (int, float, Decimal):
        return "number"
    if annotation is datetime:
        return "datetime"
    if annotation is date:
        return "date"
    return "text"


class Record(BaseModel):
    """A row of a dataset. Subclass it with `dataset=...`, and optionally `label=...` (its display name;
    `title` would be taken by pydantic), `time=...` when it has several Time fields, `kind="snapshot"`
    and `key=...` for snapshots, and `version=...` when its fields change."""

    model_config = ConfigDict(extra="forbid")

    __dataset__: ClassVar[Dataset]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        # The class keywords (dataset=..., time=...) are for __pydantic_init_subclass__ below.
        super().__init_subclass__()

    @classmethod
    def __pydantic_init_subclass__(
        cls,
        *,
        dataset: str,
        label: str | None = None,
        kind: Literal["event", "snapshot"] = "event",
        time: str | None = None,
        key: str | None = None,
        version: int = 1,
        **kwargs: Any,
    ) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        fields: list[DatasetField] = []
        for name, info in cls.model_fields.items():
            extra = info.json_schema_extra if isinstance(info.json_schema_extra, dict) else {}
            role = FieldRole(str(extra.get("role", FieldRole.TEXT.value)))
            fields.append(
                DatasetField(
                    name,
                    info.title or name,
                    _field_type(info.annotation, info.metadata),
                    role,
                    info.description,
                )
            )
        times = [f.name for f in fields if f.role == FieldRole.TIME]
        time_field = time or (times[0] if len(times) == 1 else None)
        if time_field is None or time_field not in times:
            raise TypeError(
                f"{cls.__name__}: name its main Time field with time=... ({times or 'none found'})"
            )
        if kind == "snapshot" and (key is None or key not in cls.model_fields):
            raise TypeError(f"{cls.__name__}: a snapshot dataset needs key=<field>")
        spec = Dataset(dataset, label or cls.__name__, kind, version, time_field, key, tuple(fields), cls)
        existing = DATASETS.get(dataset)
        if existing is not None and existing.model.__qualname__ != cls.__qualname__:
            raise TypeError(f"Dataset {dataset!r} is already defined by {existing.model.__name__}")
        DATASETS[dataset] = spec
        cls.__dataset__ = spec

    def occurred_at(self) -> datetime:
        value = getattr(self, self.__dataset__.time_field)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=UTC)
        raise ValueError(f"{type(self).__name__}.{self.__dataset__.time_field} has no value")

    def record_key(self) -> str | None:
        key = self.__dataset__.key_field
        return None if key is None else str(getattr(self, key))
