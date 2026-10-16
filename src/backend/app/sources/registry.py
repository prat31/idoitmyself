from app.core.errors import InvalidRequestError
from app.models.source import Source, SourceType
from app.sources.base import SourceConnector

_connectors: dict[SourceType, type[SourceConnector]] = {}


def register_connector[C: type[SourceConnector]](connector_cls: C) -> C:
    """Class decorator that makes a connector available for its source type."""
    _connectors[connector_cls.source_type] = connector_cls
    return connector_cls


def get_connector(source: Source) -> SourceConnector:
    connector_cls = _connectors.get(source.type)
    if connector_cls is None:
        raise InvalidRequestError(f"No connector is available for source type '{source.type}'")
    return connector_cls(source)
