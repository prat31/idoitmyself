from pydantic import BaseModel


class Page[T](BaseModel):
    """A slice of a larger result set."""

    items: list[T]
    total: int
    limit: int
    offset: int
