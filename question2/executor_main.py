from __future__ import annotations

import concurrent.futures
import json
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any

from question2.lib.exceptions import TaskTimeoutError, TaskValidationError
from question2.lib.logging_utils import setup_logging
from question2.lib.models import RetryConfig, TaskConfig, TaskResult, TaskStatus
from question2.lib.registry import get_task_class, registered_task_types

# Import task implementations so decorators register them.
from question2.lib import tasks  # noqa: F401


logger = logging.getLogger("task_executor.executor")


class TaskExecutor:
    """Execute operational tasks with retry and timeout handling."""

    def __init__(self, parent_logger: logging.Logger | None = None):
        """Initialize task executor with logger and empty result collection."""
        self.logger = parent_logger or setup_logging()
        self.results: list[TaskResult] = []

        logger.debug("TaskExecutor initialized")

    def run_task(self, config: TaskConfig) -> TaskResult:
        """Execute a single task with retry and timeout handling."""
        self.logger.info(
            "Task execution requested",
            extra={"task_id": config.task_id, "event": "task_execution_requested"},
        )

        started_at = datetime.now(timezone.utc)
        last_error: Exception | None = None
        last_status = TaskStatus.FAILED

        self._validate_runtime_config(config)

        for attempt in range(1, config.retry.max_attempts + 1):
            self.logger.info(
                "Starting task attempt",
                extra={
                    "task_id": config.task_id,
                    "attempt": attempt,
                    "event": "task_attempt_started",
                },
            )

            try:
                result_data = self._execute_with_timeout(config)

                self.logger.info(
                    "Task completed successfully",
                    extra={
                        "task_id": config.task_id,
                        "attempt": attempt,
                        "event": "task_succeeded",
                    },
                )

                return TaskResult(
                    task_id=config.task_id,
                    status=TaskStatus.SUCCESS,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    result_data=result_data,
                    attempts=attempt,
                )

            except TaskTimeoutError as exc:
                last_error = exc
                last_status = TaskStatus.TIMEOUT

                self.logger.error(
                    "Task attempt timed out",
                    extra={
                        "task_id": config.task_id,
                        "attempt": attempt,
                        "event": "task_timeout",
                    },
                    exc_info=True,
                )

            except Exception as exc:
                last_error = exc
                last_status = TaskStatus.FAILED

                self.logger.error(
                    "Task attempt failed",
                    extra={
                        "task_id": config.task_id,
                        "attempt": attempt,
                        "event": "task_failed",
                    },
                    exc_info=True,
                )

            if attempt < config.retry.max_attempts:
                delay = self._calculate_backoff_delay(config.retry, attempt)

                self.logger.warning(
                    "Retry scheduled",
                    extra={
                        "task_id": config.task_id,
                        "attempt": attempt,
                        "event": "task_retry_scheduled",
                    },
                )

                time.sleep(delay)

        self.logger.error(
            "Task exhausted all retry attempts",
            extra={
                "task_id": config.task_id,
                "event": "task_retries_exhausted",
            },
        )

        return TaskResult(
            task_id=config.task_id,
            status=last_status,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            error_message=str(last_error) if last_error else "unknown error",
            attempts=config.retry.max_attempts,
        )

    def _validate_runtime_config(self, config: TaskConfig) -> None:
        """Validate runtime task configuration before execution."""
        self.logger.debug(
            "Validating runtime task configuration",
            extra={"task_id": config.task_id, "event": "task_runtime_validation_started"},
        )

        if config.retry.max_attempts < 1:
            raise TaskValidationError(config.task_id, "max_attempts must be >= 1")

        if config.timeout_seconds is not None and config.timeout_seconds <= 0:
            raise TaskValidationError(config.task_id, "timeout_seconds must be positive or None")

        self.logger.debug(
            "Runtime task configuration validation completed",
            extra={"task_id": config.task_id, "event": "task_runtime_validation_completed"},
        )

    def _execute_with_timeout(self, config: TaskConfig) -> dict[str, Any]:
        """Execute task implementation and enforce configured timeout."""
        self.logger.debug(
            "Resolving task implementation",
            extra={"task_id": config.task_id, "event": "task_class_resolution_started"},
        )

        task_class = get_task_class(config.task_type)
        task = task_class(config, self.logger)

        self.logger.debug(
            "Task implementation resolved",
            extra={"task_id": config.task_id, "event": "task_class_resolved"},
        )

        if not task.validate():
            raise TaskValidationError(config.task_id, "task-specific validation returned False")

        self.logger.debug(
            "Submitting task to worker thread",
            extra={"task_id": config.task_id, "event": "task_submitted_to_worker"},
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(task.execute)

            try:
                result = future.result(timeout=config.timeout_seconds)

                self.logger.debug(
                    "Worker returned task result",
                    extra={"task_id": config.task_id, "event": "task_worker_completed"},
                )

                return result

            except concurrent.futures.TimeoutError as exc:
                cancelled = future.cancel()

                self.logger.error(
                    "Worker timeout reached",
                    extra={"task_id": config.task_id, "event": "task_worker_timeout"},
                )

                if not cancelled:
                    self.logger.warning(
                        "Timed-out worker could not be cancelled immediately",
                        extra={
                            "task_id": config.task_id,
                            "event": "task_worker_cancel_failed",
                        },
                    )

                raise TaskTimeoutError(config.task_id, config.timeout_seconds) from exc

    @staticmethod
    def _calculate_backoff_delay(retry: RetryConfig, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        exponential_delay = retry.base_delay_seconds * (2 ** (attempt - 1))
        capped_delay = min(exponential_delay, retry.max_delay_seconds)
        jitter = random.uniform(0, retry.jitter_seconds)
        return capped_delay + jitter

    def run_all(self, configs: list[TaskConfig]) -> list[TaskResult]:
        """Run multiple tasks sequentially and collect all results."""
        self.logger.info(
            "Batch task execution started",
            extra={"event": "batch_execution_started"},
        )

        self.results = []

        for config in configs:
            self.logger.debug(
                "Running next task in batch",
                extra={"task_id": config.task_id, "event": "batch_task_started"},
            )

            result = self.run_task(config)
            self.results.append(result)

            self.logger.debug(
                "Task result stored",
                extra={"task_id": config.task_id, "event": "batch_task_result_stored"},
            )

        self.logger.info(
            "Batch task execution completed",
            extra={"event": "batch_execution_completed"},
        )

        return self.results

    def summary(self) -> dict[str, Any]:
        """Return aggregate execution statistics."""
        self.logger.debug("Building execution summary", extra={"event": "summary_started"})

        total = len(self.results)
        by_status: dict[str, int] = {}
        total_attempts = 0

        for result in self.results:
            status = result.status.value
            by_status[status] = by_status.get(status, 0) + 1
            total_attempts += result.attempts

        summary = {
            "total": total,
            "by_status": by_status,
            "success_rate": by_status.get("success", 0) / total if total else 0,
            "total_attempts": total_attempts,
            "retried_tasks": sum(1 for result in self.results if result.attempts > 1),
            "registered_task_types": registered_task_types(),
        }

        self.logger.debug("Execution summary built", extra={"event": "summary_completed"})

        return summary


def build_demo_configs() -> list[TaskConfig]:
    """Build demo task configurations for local CLI execution."""
    return [
        TaskConfig(
            task_id="check-python-org",
            task_type="http_check",
            target="https://www.python.org",
            params={"expected_status": 200},
            retry=RetryConfig(max_attempts=2),
            timeout_seconds=5,
        ),
        TaskConfig(
            task_id="check-current-file",
            task_type="file_exists",
            target=__file__,
            retry=RetryConfig(max_attempts=1),
            timeout_seconds=2,
        ),
        TaskConfig(
            task_id="timeout-demo",
            task_type="sleep",
            target="local",
            params={"duration_seconds": 2},
            retry=RetryConfig(max_attempts=2, base_delay_seconds=0.1),
            timeout_seconds=0.5,
        ),
    ]


def main() -> int:
    """Run local task executor demo."""
    demo_logger = setup_logging(log_dir="logs", stdout=True)

    demo_logger.info("Task executor demo started", extra={"event": "demo_started"})

    executor = TaskExecutor(parent_logger=demo_logger)
    executor.run_all(build_demo_configs())

    print(json.dumps(executor.summary(), indent=2))

    demo_logger.info("Task executor demo completed", extra={"event": "demo_completed"})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
