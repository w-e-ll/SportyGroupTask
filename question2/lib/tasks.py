from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from question2.lib.exceptions import TaskValidationError
from question2.lib.registry import BaseTask, register_task


logger = logging.getLogger("task_executor.tasks")


@register_task("http_check")
class HttpCheckTask(BaseTask):
    """Perform an HTTP health check against a target URL."""

    def validate(self) -> bool:
        """Validate HTTP check task configuration."""
        self.logger.debug("Validating HttpCheckTask configuration")

        if not self.config.target.strip():
            self.logger.error("HTTP check validation failed: empty target")
            raise TaskValidationError(self.config.task_id, "target URL must not be empty")

        method = self.config.params.get("method", "GET")
        if method not in {"GET", "HEAD", "POST"}:
            self.logger.error("HTTP check validation failed: unsupported method=%s", method)
            raise TaskValidationError(
                self.config.task_id,
                f"unsupported HTTP method: {method}",
            )

        expected_status = self.config.params.get("expected_status", 200)
        if not isinstance(expected_status, int):
            self.logger.error(
                "HTTP check validation failed: expected_status must be int, got=%s",
                type(expected_status).__name__,
            )
            raise TaskValidationError(self.config.task_id, "expected_status must be an integer")

        self.logger.debug("HttpCheckTask validation completed")
        return True

    def execute(self) -> dict[str, Any]:
        """Execute HTTP request and validate expected status code."""
        target = self.config.target
        expected_status = self.config.params.get("expected_status", 200)
        method = self.config.params.get("method", "GET")

        self.logger.info(
            "Starting HTTP check: method=%s target=%s expected_status=%s",
            method,
            target,
            expected_status,
        )

        request = urllib.request.Request(target, method=method)

        try:
            self.logger.debug("Opening HTTP request: target=%s", target)

            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout_seconds,
            ) as response:
                actual_status = response.status

            self.logger.info(
                "HTTP response received: target=%s status=%s",
                target,
                actual_status,
            )

        except urllib.error.HTTPError as exc:
            actual_status = exc.code
            self.logger.warning(
                "HTTP error response received: target=%s status=%s",
                target,
                actual_status,
            )

        except urllib.error.URLError as exc:
            self.logger.error(
                "HTTP connection failed: target=%s reason=%s",
                target,
                exc.reason,
            )
            raise RuntimeError(f"Connection failed: {exc.reason}") from exc

        if actual_status != expected_status:
            self.logger.error(
                "HTTP status mismatch: target=%s expected=%s actual=%s",
                target,
                expected_status,
                actual_status,
            )
            raise RuntimeError(
                f"Status mismatch: expected {expected_status}, got {actual_status}"
            )

        self.logger.info("HTTP check completed successfully: target=%s", target)

        return {
            "url": target,
            "status_code": actual_status,
            "healthy": True,
        }


@register_task("file_exists")
class FileExistsTask(BaseTask):
    """Check whether a local filesystem path exists."""

    def validate(self) -> bool:
        """Validate file existence task configuration."""
        self.logger.debug("Validating FileExistsTask configuration")

        if not self.config.target.strip():
            self.logger.error("FileExistsTask validation failed: empty target")
            raise TaskValidationError(self.config.task_id, "target path must not be empty")

        self.logger.debug("FileExistsTask validation completed")
        return True

    def execute(self) -> dict[str, Any]:
        """Check target path and return filesystem metadata."""
        path = Path(self.config.target)

        self.logger.info("Checking filesystem path: path=%s", path)

        if not path.exists():
            self.logger.error("Filesystem path does not exist: path=%s", path)
            raise FileNotFoundError(f"File does not exist: {path}")

        result = {
            "path": str(path),
            "exists": True,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
        }

        self.logger.info(
            "Filesystem path check completed: path=%s is_file=%s is_dir=%s",
            path,
            result["is_file"],
            result["is_dir"],
        )

        return result


@register_task("sleep")
class SleepTask(BaseTask):
    """Sleep for a configured duration to demonstrate timeout behavior."""

    def validate(self) -> bool:
        """Validate sleep task configuration."""
        self.logger.debug("Validating SleepTask configuration")

        duration = self.config.params.get("duration_seconds", 1)

        try:
            duration_float = float(duration)
        except (TypeError, ValueError) as exc:
            self.logger.error("SleepTask validation failed: invalid duration=%s", duration)
            raise TaskValidationError(
                self.config.task_id,
                "duration_seconds must be numeric",
            ) from exc

        if duration_float < 0:
            self.logger.error("SleepTask validation failed: negative duration=%s", duration_float)
            raise TaskValidationError(
                self.config.task_id,
                "duration_seconds must be >= 0",
            )

        self.logger.debug("SleepTask validation completed: duration=%s", duration_float)
        return True

    def execute(self) -> dict[str, Any]:
        """Sleep for the configured number of seconds."""
        duration = float(self.config.params.get("duration_seconds", 1))

        self.logger.info("Sleep task started: duration_seconds=%s", duration)

        time.sleep(duration)

        self.logger.info("Sleep task completed: duration_seconds=%s", duration)

        return {
            "slept_seconds": duration,
        }
