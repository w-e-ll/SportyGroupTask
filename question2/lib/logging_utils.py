from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path


class MaxLevelFilter(logging.Filter):
    """Allow log records up to and including a maximum level."""

    def __init__(self, max_level: int):
        """Store the maximum accepted log level."""
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True when the record level is lower than or equal to max_level."""
        return record.levelno <= self.max_level


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for production-friendly parsing."""

    def format(self, record: logging.LogRecord) -> str:
        """Convert a logging record into a JSON string."""
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
        }

        if hasattr(record, "task_id"):
            payload["task_id"] = record.task_id

        if hasattr(record, "attempt"):
            payload["attempt"] = record.attempt

        if hasattr(record, "event"):
            payload["event"] = record.event

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def setup_logging(
    logger_name: str = "task_executor",
    log_dir: str | Path | None = None,
    level: int = logging.INFO,
    stdout: bool = True,
) -> logging.Logger:
    """Create a logger with JSON stdout and optional split info/error log files."""
    logger = logging.getLogger(logger_name)
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
        info_log = log_path / f"task_executor-info-{date_suffix}.log"
        error_log = log_path / f"task_executor-error-{date_suffix}.log"

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
        "Logger initialized",
        extra={"event": "logger_initialized"},
    )

    return logger


def get_module_logger(module_name: str) -> logging.Logger:
    """Return a child logger for a specific module."""
    return logging.getLogger(f"task_executor.{module_name}")
