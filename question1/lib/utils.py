from __future__ import annotations

import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from question1.lib.exceptions import InvalidConfigError, UnsupportedFormatError
from question1.lib.models import ChangeType, ConfigSourceResult, Conflict, DiffEntry, SourceStatus


logger = logging.getLogger("config_resolver.utils")


SENSITIVE_KEYWORDS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
)


def load_yaml_file(path: Path) -> ConfigSourceResult:
    """Load YAML configuration file into a source result."""
    logger.info(
        "Loading YAML configuration file",
        extra={"event": "yaml_load_started", "config_path": str(path)},
    )

    try:
        if path.suffix.lower() not in {".yml", ".yaml"}:
            logger.error(
                "Unsupported configuration file format",
                extra={"event": "unsupported_config_format", "config_path": str(path)},
            )
            raise UnsupportedFormatError(f"Unsupported config format: {path.suffix}")

        if not path.exists():
            logger.error(
                "Configuration file does not exist",
                extra={"event": "config_file_missing", "config_path": str(path)},
            )
            raise FileNotFoundError(f"Configuration file does not exist: {path}")

        if not path.is_file():
            logger.error(
                "Configuration path is not a file",
                extra={"event": "config_path_not_file", "config_path": str(path)},
            )
            raise InvalidConfigError(f"Configuration path is not a file: {path}")

        with path.open("r", encoding="utf-8") as file_obj:
            data = yaml.safe_load(file_obj) or {}

        if not isinstance(data, dict):
            logger.error(
                "Top-level YAML value is not a mapping",
                extra={"event": "invalid_yaml_top_level", "config_path": str(path)},
            )
            raise InvalidConfigError("Top-level YAML value must be a mapping/object")

        logger.info(
            "YAML configuration loaded successfully",
            extra={"event": "yaml_load_completed", "config_path": str(path)},
        )

        return ConfigSourceResult(
            name=f"file:{path}",
            status=SourceStatus.LOADED,
            data=data,
        )

    except Exception as exc:
        logger.error(
            "Failed to load YAML configuration",
            extra={"event": "yaml_load_failed", "config_path": str(path)},
            exc_info=True,
        )

        return ConfigSourceResult(
            name=f"file:{path}",
            status=SourceStatus.UNAVAILABLE,
            data={},
            error=str(exc),
        )


def parse_env(prefix: str) -> ConfigSourceResult:
    """Parse environment variables matching a prefix into nested config."""
    logger.info("Parsing environment overrides", extra={"event": "env_parse_started"})

    data: dict[str, Any] = {}

    try:
        if not prefix or not prefix.strip():
            logger.error("Environment prefix is empty", extra={"event": "empty_env_prefix"})
            raise InvalidConfigError("Environment prefix must not be empty")

        normalized_prefix = prefix.strip()
        matched_count = 0

        for raw_key, value in os.environ.items():
            if not raw_key.startswith(normalized_prefix):
                continue

            matched_count += 1
            key_path = raw_key.removeprefix(normalized_prefix).lower().split("__")

            logger.debug(
                "Parsing environment override",
                extra={"event": "env_override_found", "source": raw_key},
            )

            set_nested_value(data, key_path, parse_scalar(value))

        logger.info(
            "Environment overrides parsed",
            extra={"event": "env_parse_completed", "source": f"env:{normalized_prefix}"},
        )

        logger.debug("Environment override count=%s", matched_count)

        return ConfigSourceResult(
            name=f"env:{normalized_prefix}",
            status=SourceStatus.LOADED,
            data=data,
        )

    except Exception as exc:
        logger.error(
            "Failed to parse environment overrides",
            extra={"event": "env_parse_failed", "source": f"env:{prefix}"},
            exc_info=True,
        )

        return ConfigSourceResult(
            name=f"env:{prefix}",
            status=SourceStatus.UNAVAILABLE,
            data={},
            error=str(exc),
        )


def parse_scalar(value: str) -> Any:
    """Convert string environment value into a scalar type."""
    logger.debug("Parsing scalar value")

    lowered = value.lower()

    if lowered == "true":
        logger.debug("Parsed scalar as boolean true")
        return True

    if lowered == "false":
        logger.debug("Parsed scalar as boolean false")
        return False

    if lowered in {"none", "null"}:
        logger.debug("Parsed scalar as null")
        return None

    try:
        parsed_int = int(value)
        logger.debug("Parsed scalar as integer")
        return parsed_int
    except ValueError:
        pass

    try:
        parsed_float = float(value)
        logger.debug("Parsed scalar as float")
        return parsed_float
    except ValueError:
        logger.debug("Keeping scalar as string")
        return value


def set_nested_value(data: dict[str, Any], path: list[str], value: Any) -> None:
    """Set a nested value inside a dictionary using a path list."""
    logger.debug("Setting nested value: path=%s", ".".join(path))

    if not isinstance(data, dict):
        logger.error("Target data is not a dictionary")
        raise InvalidConfigError("Target data must be a dictionary")

    if not path or not path[-1]:
        logger.error("Environment override key is empty")
        raise InvalidConfigError("Environment override key cannot be empty")

    current = data

    for key in path[:-1]:
        if not key:
            logger.error("Environment override path contains empty segment: path=%s", path)
            raise InvalidConfigError("Environment override path contains an empty segment")

        existing = current.get(key)

        if existing is None:
            logger.debug("Creating nested dictionary for key=%s", key)
            current[key] = {}
        elif not isinstance(existing, dict):
            logger.error("Cannot create nested value under non-object key=%s", key)
            raise InvalidConfigError(
                f"Cannot create nested override under non-object key: {key}"
            )

        current = current[key]

    current[path[-1]] = value
    logger.debug("Nested value set successfully: path=%s", ".".join(path))


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override dictionary into base dictionary."""
    logger.debug("Starting deep merge")

    if not isinstance(base, dict):
        logger.error("Deep merge base is not a dictionary")
        raise InvalidConfigError("base must be a dictionary")

    if not isinstance(override, dict):
        logger.error("Deep merge override is not a dictionary")
        raise InvalidConfigError("override must be a dictionary")

    result = deepcopy(base)

    for key, override_value in override.items():
        logger.debug("Merging key=%s", key)

        base_value = result.get(key)

        if isinstance(base_value, dict) and isinstance(override_value, dict):
            result[key] = deep_merge(base_value, override_value)
        else:
            result[key] = deepcopy(override_value)

    logger.debug("Deep merge completed")
    return result


def flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested dictionary into dotted-path dictionary."""
    logger.debug("Flattening config path prefix=%s", prefix)

    if not isinstance(data, dict):
        logger.error("Cannot flatten non-dictionary value")
        raise InvalidConfigError("data must be a dictionary")

    output: dict[str, Any] = {}

    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else str(key)

        if isinstance(value, dict):
            output.update(flatten(value, path))
        else:
            output[path] = value

    logger.debug("Flatten completed for prefix=%s entries=%s", prefix, len(output))
    return output


def detect_conflicts(staging: dict[str, Any], production: dict[str, Any]) -> list[Conflict]:
    """Detect differing values for the same paths across environments."""
    logger.info("Conflict detection started", extra={"event": "conflict_detection_started"})

    staging_flat = flatten(staging)
    production_flat = flatten(production)

    conflicts: list[Conflict] = []

    for path in sorted(staging_flat.keys() & production_flat.keys()):
        staging_value = staging_flat[path]
        production_value = production_flat[path]

        if staging_value != production_value:
            logger.debug("Conflict detected at path=%s", path)
            conflicts.append(
                Conflict(
                    path=path,
                    staging_value=staging_value,
                    production_value=production_value,
                )
            )

    logger.info(
        "Conflict detection completed",
        extra={"event": "conflict_detection_completed"},
    )
    logger.debug("Conflict count=%s", len(conflicts))

    return conflicts


def build_diff(current: dict[str, Any], desired: dict[str, Any]) -> list[DiffEntry]:
    """Build diff entries from current configuration to desired configuration."""
    logger.info("Diff build started", extra={"event": "diff_build_started"})

    current_flat = flatten(current)
    desired_flat = flatten(desired)

    diff: list[DiffEntry] = []

    for path in sorted(current_flat.keys() | desired_flat.keys()):
        exists_in_current = path in current_flat
        exists_in_desired = path in desired_flat

        if exists_in_current and not exists_in_desired:
            logger.debug("Removed diff detected at path=%s", path)
            diff.append(
                DiffEntry(
                    path=path,
                    change_type=ChangeType.REMOVED,
                    old_value=current_flat[path],
                    new_value=None,
                )
            )
        elif not exists_in_current and exists_in_desired:
            logger.debug("Added diff detected at path=%s", path)
            diff.append(
                DiffEntry(
                    path=path,
                    change_type=ChangeType.ADDED,
                    old_value=None,
                    new_value=desired_flat[path],
                )
            )
        elif current_flat[path] != desired_flat[path]:
            logger.debug("Changed diff detected at path=%s", path)
            diff.append(
                DiffEntry(
                    path=path,
                    change_type=ChangeType.CHANGED,
                    old_value=current_flat[path],
                    new_value=desired_flat[path],
                )
            )

    logger.info("Diff build completed", extra={"event": "diff_build_completed"})
    logger.debug("Diff count=%s", len(diff))

    return diff


def is_sensitive_key(path: str) -> bool:
    """Return True if config path looks sensitive."""
    if not path or not path.strip():
        logger.warning("Sensitive key check received empty path")
        return False

    normalized = path.lower()
    is_sensitive = any(keyword in normalized for keyword in SENSITIVE_KEYWORDS)

    logger.debug("Sensitive key check: path=%s result=%s", path, is_sensitive)

    return is_sensitive


def mask_value(value: Any) -> str:
    """Return masked placeholder for a sensitive value."""
    logger.debug("Masking sensitive value")

    if value is None:
        return "<masked:null>"

    return "<masked>"


def mask_sensitive_value_for_path(path: str, value: Any) -> Any:
    """Mask value when path is sensitive."""
    if is_sensitive_key(path):
        logger.debug("Masking value for sensitive path=%s", path)
        return mask_value(value)

    return value


def mask_sensitive(data: Any, parent_path: str = "") -> Any:
    """Recursively mask sensitive values in dictionaries and lists."""
    logger.debug("Masking sensitive values under parent_path=%s", parent_path)

    if isinstance(data, dict):
        masked: dict[str, Any] = {}

        for key, value in data.items():
            path = f"{parent_path}.{key}" if parent_path else str(key)
            masked[key] = (
                mask_value(value)
                if is_sensitive_key(path)
                else mask_sensitive(value, path)
            )

        return masked

    if isinstance(data, list):
        return [mask_sensitive(item, parent_path) for item in data]

    return data


def serialize_conflicts(conflicts: list[Conflict]) -> list[dict[str, Any]]:
    """Serialize conflicts into JSON-compatible dictionaries."""
    logger.debug("Serializing conflicts count=%s", len(conflicts))

    return [
        {
            "path": conflict.path,
            "staging_value": mask_sensitive_value_for_path(
                conflict.path,
                conflict.staging_value,
            ),
            "production_value": mask_sensitive_value_for_path(
                conflict.path,
                conflict.production_value,
            ),
        }
        for conflict in conflicts
    ]


def serialize_diff(diff: list[DiffEntry]) -> list[dict[str, Any]]:
    """Serialize diff entries into JSON-compatible dictionaries."""
    logger.debug("Serializing diff count=%s", len(diff))

    return [
        {
            "path": item.path,
            "change_type": item.change_type.value,
            "old_value": mask_sensitive_value_for_path(item.path, item.old_value),
            "new_value": mask_sensitive_value_for_path(item.path, item.new_value),
        }
        for item in diff
    ]
