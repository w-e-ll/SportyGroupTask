from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from question1.lib.exceptions import InvalidConfigError
from question1.lib.logging_utils import setup_logging
from question1.lib.models import ResolverResult, SourceStatus
from question1.lib.utils import (
    build_diff,
    deep_merge,
    detect_conflicts,
    load_yaml_file,
    mask_sensitive,
    parse_env,
    serialize_conflicts,
    serialize_diff,
)


logger = logging.getLogger("config_resolver.main")


def validate_file_argument(path: Path, argument_name: str) -> None:
    """Validate a CLI file path argument."""
    logger.debug(
        "Validating file argument",
        extra={
            "event": "file_argument_validation_started",
            "config_path": str(path),
        },
    )

    if path is None:
        logger.error(
            "File argument is None",
            extra={"event": "file_argument_validation_failed"},
        )
        raise InvalidConfigError(f"{argument_name} must not be None")

    if not str(path).strip():
        logger.error(
            "File argument is empty",
            extra={"event": "file_argument_validation_failed"},
        )
        raise InvalidConfigError(f"{argument_name} must not be empty")

    if path.suffix.lower() not in {".yml", ".yaml"}:
        logger.error(
            "File argument has unsupported suffix",
            extra={
                "event": "file_argument_validation_failed",
                "config_path": str(path),
            },
        )
        raise InvalidConfigError(
            f"{argument_name} must point to a .yml or .yaml file",
            source=str(path),
        )

    logger.debug(
        "File argument validation completed",
        extra={
            "event": "file_argument_validation_completed",
            "config_path": str(path),
        },
    )


def validate_env_prefix(prefix: str, argument_name: str) -> None:
    """Validate an environment variable prefix argument."""
    logger.debug(
        "Validating environment prefix",
        extra={"event": "env_prefix_validation_started", "source": argument_name},
    )

    if not prefix or not prefix.strip():
        logger.error(
            "Environment prefix validation failed",
            extra={"event": "env_prefix_validation_failed", "source": argument_name},
        )
        raise InvalidConfigError(f"{argument_name} must not be empty")

    logger.debug(
        "Environment prefix validation completed",
        extra={"event": "env_prefix_validation_completed", "source": argument_name},
    )


def collect_source_failure(source_name: str, error: str | None) -> dict[str, str]:
    """Build a structured source failure entry."""
    logger.debug(
        "Collecting source failure",
        extra={"event": "source_failure_collected", "source": source_name},
    )

    if not source_name or not source_name.strip():
        logger.error("Cannot collect source failure with empty source name")
        raise InvalidConfigError("source name must not be empty")

    return {
        "source": source_name,
        "error": error or "unknown error",
    }


def resolve_environment(
    file_path: Path,
    env_prefix: str,
    parent_logger: logging.Logger,
    environment: str,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Load and merge file config with environment overrides."""
    parent_logger.info(
        "Environment resolution started",
        extra={
            "event": "environment_resolution_started",
            "environment": environment,
            "config_path": str(file_path),
        },
    )

    validate_file_argument(file_path, f"{environment}_file")
    validate_env_prefix(env_prefix, f"{environment}_env_prefix")

    file_source = load_yaml_file(file_path)
    env_source = parse_env(env_prefix)

    failures: list[dict[str, str]] = []

    for source in (file_source, env_source):
        parent_logger.info(
            "Source loaded",
            extra={
                "event": "source_loaded",
                "source": source.name,
                "environment": environment,
            },
        )

        if source.status == SourceStatus.UNAVAILABLE:
            parent_logger.warning(
                "Source unavailable",
                extra={
                    "event": "source_unavailable",
                    "source": source.name,
                    "environment": environment,
                },
            )

            failures.append(
                collect_source_failure(
                    source_name=source.name,
                    error=source.error,
                )
            )

    merged = deep_merge(file_source.data, env_source.data)

    parent_logger.info(
        "Environment resolution completed",
        extra={
            "event": "environment_resolution_completed",
            "environment": environment,
        },
    )

    return merged, failures


def build_response(result: ResolverResult) -> dict[str, Any]:
    """Build JSON-serializable resolver response."""
    logger.debug("Building resolver response", extra={"event": "response_build_started"})

    response = {
        "dry_run": result.dry_run,
        "dry_run_note": (
            "Current implementation is non-mutating. "
            "--dry-run explicitly signals preview intent and is future-compatible "
            "with potential apply/write functionality."
        ),
        "source_failures": result.source_failures,
        "staging_effective_config": result.staging_effective_config,
        "production_effective_config": result.production_effective_config,
        "conflicts": serialize_conflicts(result.conflicts),
        "diff_production_to_staging": serialize_diff(result.diff),
        "summary": result.summary,
    }

    logger.debug("Resolver response built", extra={"event": "response_build_completed"})

    return response


def run(
    staging_file: Path,
    production_file: Path,
    staging_env_prefix: str,
    production_env_prefix: str,
    dry_run: bool,
    log_dir: str | Path | None = "logs",
    stdout: bool = True,
) -> dict[str, Any]:
    """Run configuration conflict resolution workflow."""
    main_logger = setup_logging(
        logger_name="config_resolver",
        log_dir=log_dir,
        stdout=stdout,
    )

    main_logger.info(
        "Configuration conflict resolution started",
        extra={"event": "resolver_started"},
    )

    staging_config, staging_failures = resolve_environment(
        file_path=staging_file,
        env_prefix=staging_env_prefix,
        parent_logger=main_logger,
        environment="staging",
    )

    production_config, production_failures = resolve_environment(
        file_path=production_file,
        env_prefix=production_env_prefix,
        parent_logger=main_logger,
        environment="production",
    )

    all_failures = staging_failures + production_failures

    main_logger.info(
        "Detecting conflicts",
        extra={"event": "conflict_detection_requested"},
    )
    conflicts = detect_conflicts(staging_config, production_config)

    main_logger.info(
        "Building production-to-staging diff",
        extra={"event": "diff_build_requested"},
    )
    diff = build_diff(current=production_config, desired=staging_config)

    result = ResolverResult(
        dry_run=dry_run,
        staging_effective_config=mask_sensitive(staging_config),
        production_effective_config=mask_sensitive(production_config),
        conflicts=conflicts,
        diff=diff,
        source_failures=all_failures,
    )

    response = build_response(result)

    main_logger.info(
        "Configuration conflict resolution completed",
        extra={"event": "resolver_completed"},
    )

    return response


def build_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Configuration Conflict Resolver",
    )

    parser.add_argument(
        "--staging-file",
        required=True,
        type=Path,
        help="Path to staging YAML configuration file.",
    )
    parser.add_argument(
        "--production-file",
        required=True,
        type=Path,
        help="Path to production YAML configuration file.",
    )
    parser.add_argument(
        "--staging-env-prefix",
        default="STAGING_",
        help="Environment variable prefix for staging overrides.",
    )
    parser.add_argument(
        "--production-env-prefix",
        default="PRODUCTION_",
        help="Environment variable prefix for production overrides.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Preview changes only. Current implementation is non-mutating; "
            "this flag is explicit operator intent and future-compatible "
            "with apply/write mode."
        ),
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for split JSON log files.",
    )
    parser.add_argument(
        "--no-stdout",
        action="store_true",
        help="Disable JSON logs on stdout.",
    )

    return parser


def main() -> int:
    """Run resolver from command line."""
    args = build_parser().parse_args()

    output = run(
        staging_file=args.staging_file,
        production_file=args.production_file,
        staging_env_prefix=args.staging_env_prefix,
        production_env_prefix=args.production_env_prefix,
        dry_run=args.dry_run,
        log_dir=args.log_dir,
        stdout=not args.no_stdout,
    )

    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
