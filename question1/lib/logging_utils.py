from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path


class MaxLevelFilter(logging.Filter):
    """Allow records up to a maximum logging level."""

    def __init__(self, max_level: int):
        """Store maximum accepted log level."""
        super().__init__()

        if max_level < logging.NOTSET:
            raise ValueError("max_level must be a valid logging level")

        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True when record level is less than or equal to max_level."""
        return record.levelno <= self.max_level


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Convert a log record into a JSON string."""
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
        }

        if hasattr(record, "event"):
            payload["event"] = record.event

        if hasattr(record, "source"):
            payload["source"] = record.source

        if hasattr(record, "config_path"):
            payload["config_path"] = record.config_path

        if hasattr(record, "environment"):
            payload["environment"] = record.environment

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def setup_logging(
    logger_name: str = "config_resolver",
    log_dir: str | Path | None = None,
    level: int = logging.INFO,
    stdout: bool = True,
) -> logging.Logger:
    """Create JSON logger with stdout and optional split info/error files."""
    if not logger_name or not logger_name.strip():
        raise ValueError("logger_name must not be empty")

    logger = logging.getLogger(logger_name.strip())
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = JsonFormatter()

    if stdout:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(level)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)

    if log_dir is not None:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        date_suffix = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        info_log = log_path / f"config_resolver-info-{date_suffix}.log"
        error_log = log_path / f"config_resolver-error-{date_suffix}.log"

        info_handler = logging.handlers.RotatingFileHandler(
            info_log,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        info_handler.setLevel(logging.DEBUG)
        info_handler.addFilter(MaxLevelFilter(logging.WARNING))
        info_handler.setFormatter(formatter)
        logger.addHandler(info_handler)

        error_handler = logging.handlers.RotatingFileHandler(
            error_log,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    logger.debug(
        "Config resolver logger initialized",
        extra={"event": "logger_initialized"},
    )

    return logger


def get_module_logger(module_name: str) -> logging.Logger:
    """Return child logger for a config resolver module."""
    if not module_name or not module_name.strip():
        raise ValueError("module_name must not be empty")

    return logging.getLogger(f"config_resolver.{module_name.strip()}")
