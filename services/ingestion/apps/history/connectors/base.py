"""Common, checkpoint-aware source connector contracts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

@dataclass(frozen=True)
class ConnectorItem:
    external_reference: str
    url: str
    title: str
    published_at: datetime | None
    metadata: dict[str, Any]

@dataclass(frozen=True)
class ConnectorResult:
    items: tuple[ConnectorItem, ...]
    cursor: dict[str, Any]
    not_modified: bool = False

class SourceConnector(Protocol):
    key: str
    def discover(self, subject_source: Any, *, cursor: dict[str, Any]) -> ConnectorResult: ...
    def fetch(self, item: ConnectorItem) -> bytes: ...
    def normalize(self, item: ConnectorItem) -> dict[str, Any]: ...

def connector_metadata(config: Any) -> dict[str, Any]:
    """Export reviewable configuration only; never include a secret value."""
    return {
        "connector_key": config.connector_key,
        "schema_version": config.schema_version,
        "endpoint": config.endpoint,
        "allowed_domain": config.allowed_domain,
        "secret_env_reference": config.secret_env_reference,
        "enabled": config.enabled,
        "coverage_tracks": config.coverage_tracks,
        "coverage_start": config.coverage_start.isoformat() if config.coverage_start else None,
        "coverage_end": config.coverage_end.isoformat() if config.coverage_end else None,
        "requests_per_minute": config.requests_per_minute,
        "monthly_cost_limit": str(config.monthly_cost_limit) if config.monthly_cost_limit is not None else None,
    }