from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


logger = logging.getLogger("config_resolver.models")


class SourceStatus(str, Enum):
    """Configuration source loading status."""

    LOADED = "loaded"
    UNAVAILABLE = "unavailable"


class ChangeType(str, Enum):
    """Supported diff change types."""

    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


class ConfigFormat(str, Enum):
    """Supported configuration file formats."""

    YAML = "yaml"


@dataclass(frozen=True)
class ConfigSourceResult:
    """Result of loading one configuration source."""

    name: str
    status: SourceStatus
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        """Validate source result after initialization."""
        logger.debug("Validating ConfigSourceResult: source=%s status=%s", self.name, self.status.value)

        if not self.name.strip():
            logger.error("ConfigSourceResult validation failed: empty source name")
            raise ValueError("source name must not be empty")

        if not isinstance(self.data, dict):
            logger.error("ConfigSourceResult validation failed for source=%s: data is not dict", self.name)
            raise TypeError("source data must be a dictionary")

        if self.status == SourceStatus.UNAVAILABLE and not self.error:
            logger.warning("Unavailable source has no error message: source=%s", self.name)

        logger.debug("ConfigSourceResult validation completed: source=%s", self.name)


@dataclass(frozen=True)
class Conflict:
    """Configuration conflict between staging and production."""

    path: str
    staging_value: Any
    production_value: Any

    def __post_init__(self) -> None:
        """Validate conflict after initialization."""
        logger.debug("Validating Conflict: path=%s", self.path)

        if not self.path.strip():
            logger.error("Conflict validation failed: empty path")
            raise ValueError("conflict path must not be empty")

        if self.staging_value == self.production_value:
            logger.warning("Conflict created with equal values: path=%s", self.path)

        logger.debug("Conflict validation completed: path=%s", self.path)


@dataclass(frozen=True)
class DiffEntry:
    """Single diff entry between current and desired config."""

    path: str
    change_type: ChangeType
    old_value: Any = None
    new_value: Any = None

    def __post_init__(self) -> None:
        """Validate diff entry after initialization."""
        logger.debug("Validating DiffEntry: path=%s change_type=%s", self.path, self.change_type.value)

        if not self.path.strip():
            logger.error("DiffEntry validation failed: empty path")
            raise ValueError("diff path must not be empty")

        if self.change_type == ChangeType.ADDED and self.new_value is None:
            logger.warning("Added diff entry has no new_value: path=%s", self.path)

        if self.change_type == ChangeType.REMOVED and self.old_value is None:
            logger.warning("Removed diff entry has no old_value: path=%s", self.path)

        if self.change_type == ChangeType.CHANGED and self.old_value == self.new_value:
            logger.warning("Changed diff entry has equal values: path=%s", self.path)

        logger.debug("DiffEntry validation completed: path=%s", self.path)


@dataclass(frozen=True)
class ResolverResult:
    """Final configuration resolver result."""

    dry_run: bool
    staging_effective_config: dict[str, Any]
    production_effective_config: dict[str, Any]
    conflicts: list[Conflict]
    diff: list[DiffEntry]
    source_failures: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate resolver result after initialization."""
        logger.debug("Validating ResolverResult")

        if not isinstance(self.staging_effective_config, dict):
            logger.error("ResolverResult validation failed: staging config is not dict")
            raise TypeError("staging_effective_config must be a dictionary")

        if not isinstance(self.production_effective_config, dict):
            logger.error("ResolverResult validation failed: production config is not dict")
            raise TypeError("production_effective_config must be a dictionary")

        if not isinstance(self.conflicts, list):
            logger.error("ResolverResult validation failed: conflicts is not list")
            raise TypeError("conflicts must be a list")

        if not isinstance(self.diff, list):
            logger.error("ResolverResult validation failed: diff is not list")
            raise TypeError("diff must be a list")

        logger.debug(
            "ResolverResult validation completed: conflicts=%s diff=%s failures=%s",
            len(self.conflicts),
            len(self.diff),
            len(self.source_failures),
        )

    @property
    def summary(self) -> dict[str, int]:
        """Return aggregate resolver statistics."""
        logger.debug("Building ResolverResult summary")

        return {
            "conflict_count": len(self.conflicts),
            "diff_count": len(self.diff),
            "source_failure_count": len(self.source_failures),
        }
