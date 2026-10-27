"""Processor kinds: the code. A kind is a ProcessorKind subclass with a `key`; defining one registers
it. Kinds live in packages under app/processors/ (e.g. app/processors/cards/), which are imported to
discover them. See .claude/skills/add-processor for how to write one."""

import importlib
import json
import pkgutil
import sys
from functools import cache
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel

from app.processors.context import Context
from app.processors.document import EmailDocument
from app.processors.records import Record

_KINDS: dict[str, "ProcessorKind"] = {}


class ProcessorKind:
    """Subclass, set the class attributes and implement `process`."""

    key: ClassVar[str]  # stable id, stored on processors
    name: ClassVar[str]
    description: ClassVar[str]
    # Bump when what it writes changes: runs record it, so old results can be found and re-run.
    version: ClassVar[int] = 1
    # The datasets it writes (Record classes). Writing anything else fails the run.
    writes: ClassVar[tuple[type[Record], ...]] = ()
    # A Pydantic model for the processor's settings, if it has any (validated on save).
    config: ClassVar[type[BaseModel] | None] = None
    # Its default dashboard: a JSON file next to the kind's module (see app.dashboards).
    dashboard: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "key" not in cls.__dict__:
            return  # an abstract base for other kinds
        if cls.key in _KINDS:
            raise TypeError(f"Processor kind {cls.key!r} is defined twice")
        _KINDS[cls.key] = cls()

    async def process(self, doc: EmailDocument, ctx: Context) -> None:
        """Read the email, then `ctx.write(...)` records and `ctx.action(...)` side effects. Raise Skip,
        Fail, NeedsInput or Retry (app.processors.outcomes) to end otherwise."""
        raise NotImplementedError

    def dashboard_spec(self) -> dict[str, Any] | None:
        if self.dashboard is None:
            return None
        path = Path(sys.modules[type(self).__module__].__file__ or "").parent / self.dashboard
        return json.loads(path.read_text())


@cache
def kinds() -> dict[str, ProcessorKind]:
    """Every kind, by key: imports each package under app/processors/ once."""
    package = importlib.import_module("app.processors")
    for module in pkgutil.iter_modules(package.__path__):
        if module.ispkg:
            importlib.import_module(f"app.processors.{module.name}")
    return dict(_KINDS)
