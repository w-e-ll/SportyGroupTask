from __future__ import annotations

import logging
from pathlib import Path

import pytest

from question2.executor_main import TaskExecutor
from question2.lib.exceptions import (
    DuplicateTaskTypeError,
    TaskTimeoutError,
    TaskValidationError,
    UnknownTaskTypeError,
)
from question2.lib.logging_utils import setup_logging
from question2.lib.models import RetryConfig, TaskConfig, TaskStatus
from question2.lib.registry import BaseTask, get_task_class, register_task, registered_task_types


logger = logging.getLogger("task_executor.tests")


def test_retry_config_rejects_invalid_max_attempts():
    """Verify retry config rejects invalid max_attempts."""
    logger.info("Testing invalid RetryConfig max_attempts validation")

    with pytest.raises(ValueError, match="max_attempts"):
        RetryConfig(max_attempts=0)


def test_retry_config_rejects_invalid_delay_order():
    """Verify retry config rejects invalid delay ordering."""
    logger.info("Testing invalid RetryConfig delay validation")

    with pytest.raises(ValueError, match="max_delay_seconds"):
        RetryConfig(base_delay_seconds=2.0, max_delay_seconds=1.0)


def test_task_config_rejects_empty_task_id():
    """Verify task config rejects empty task_id."""
    logger.info("Testing empty task_id validation")

    with pytest.raises(ValueError, match="task_id"):
        TaskConfig(task_id="", task_type="file_exists", target="some-file")


def test_task_config_rejects_invalid_timeout():
    """Verify task config rejects non-positive timeout."""
    logger.info("Testing invalid timeout validation")

    with pytest.raises(ValueError, match="timeout_seconds"):
        TaskConfig(
            task_id="bad-timeout",
            task_type="file_exists",
            target="some-file",
            timeout_seconds=0,
        )


def test_registered_task_types_contains_default_tasks():
    """Verify built-in task types are registered through decorators."""
    logger.info("Testing default task type registration")

    task_types = registered_task_types()

    assert "file_exists" in task_types
    assert "http_check" in task_types
    assert "sleep" in task_types


def test_get_task_class_rejects_unknown_task_type():
    """Verify unknown task types raise a typed exception."""
    logger.info("Testing unknown task type handling")

    with pytest.raises(UnknownTaskTypeError):
        get_task_class("does_not_exist")


def test_duplicate_task_registration_is_rejected():
    """Verify duplicate task registration is rejected."""
    logger.info("Testing duplicate task type registration")

    with pytest.raises(DuplicateTaskTypeError):

        @register_task("file_exists")
        class DuplicateFileExistsTask(BaseTask):
            """Temporary duplicate task used only for validation."""

            def execute(self) -> dict:
                """Return dummy result."""
                return {}


def test_file_exists_task_success(tmp_path: Path):
    """Verify file_exists task succeeds for an existing file."""
    logger.info("Testing successful file_exists task execution")

    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello", encoding="utf-8")

    executor = TaskExecutor(parent_logger=setup_logging(stdout=False))
    result = executor.run_task(
        TaskConfig(
            task_id="file-check-success",
            task_type="file_exists",
            target=str(file_path),
            retry=RetryConfig(max_attempts=1),
            timeout_seconds=2,
        )
    )

    assert result.status == TaskStatus.SUCCESS
    assert result.result_data["exists"] is True
    assert result.result_data["is_file"] is True
    assert result.attempts == 1


def test_file_exists_task_failure_retries(tmp_path: Path):
    """Verify failed file_exists task retries and returns FAILED."""
    logger.info("Testing failed file_exists task with retries")

    missing_file = tmp_path / "missing.txt"

    executor = TaskExecutor(parent_logger=setup_logging(stdout=False))
    result = executor.run_task(
        TaskConfig(
            task_id="file-check-failure",
            task_type="file_exists",
            target=str(missing_file),
            retry=RetryConfig(
                max_attempts=2,
                base_delay_seconds=0,
                max_delay_seconds=0,
                jitter_seconds=0,
            ),
            timeout_seconds=2,
        )
    )

    assert result.status == TaskStatus.FAILED
    assert result.attempts == 2
    assert result.error_message is not None


def test_sleep_task_timeout_is_distinguishable():
    """Verify timeout task returns TIMEOUT instead of FAILED."""
    logger.info("Testing timeout behavior with sleep task")

    executor = TaskExecutor(parent_logger=setup_logging(stdout=False))
    result = executor.run_task(
        TaskConfig(
            task_id="sleep-timeout",
            task_type="sleep",
            target="local",
            params={"duration_seconds": 0.2},
            retry=RetryConfig(
                max_attempts=2,
                base_delay_seconds=0,
                max_delay_seconds=0,
                jitter_seconds=0,
            ),
            timeout_seconds=0.01,
        )
    )

    assert result.status == TaskStatus.TIMEOUT
    assert result.attempts == 2
    assert result.error_message is not None


def test_sleep_task_success():
    """Verify sleep task succeeds when timeout is sufficient."""
    logger.info("Testing successful sleep task execution")

    executor = TaskExecutor(parent_logger=setup_logging(stdout=False))
    result = executor.run_task(
        TaskConfig(
            task_id="sleep-success",
            task_type="sleep",
            target="local",
            params={"duration_seconds": 0.01},
            retry=RetryConfig(max_attempts=1),
            timeout_seconds=1,
        )
    )

    assert result.status == TaskStatus.SUCCESS
    assert result.result_data["slept_seconds"] == 0.01


def test_sleep_task_validation_rejects_negative_duration():
    """Verify sleep task rejects negative duration."""
    logger.info("Testing sleep task negative duration validation")

    executor = TaskExecutor(parent_logger=setup_logging(stdout=False))

    result = executor.run_task(
        TaskConfig(
            task_id="sleep-negative",
            task_type="sleep",
            target="local",
            params={"duration_seconds": -1},
            retry=RetryConfig(max_attempts=1),
            timeout_seconds=1,
        )
    )

    assert result.status == TaskStatus.FAILED
    assert "duration_seconds" in result.error_message


def test_backoff_delay_uses_exponential_cap_and_jitter():
    """Verify backoff delay respects exponential cap and jitter range."""
    logger.info("Testing backoff delay calculation")

    retry = RetryConfig(
        max_attempts=3,
        base_delay_seconds=1,
        max_delay_seconds=2,
        jitter_seconds=0,
    )

    assert TaskExecutor._calculate_backoff_delay(retry, attempt=1) == 1
    assert TaskExecutor._calculate_backoff_delay(retry, attempt=2) == 2
    assert TaskExecutor._calculate_backoff_delay(retry, attempt=3) == 2


def test_run_all_continues_after_failed_task(tmp_path: Path):
    """Verify failed tasks do not block later tasks from running."""
    logger.info("Testing sequential run_all failure isolation")

    existing_file = tmp_path / "exists.txt"
    existing_file.write_text("ok", encoding="utf-8")

    executor = TaskExecutor(parent_logger=setup_logging(stdout=False))

    results = executor.run_all(
        [
            TaskConfig(
                task_id="missing-file",
                task_type="file_exists",
                target=str(tmp_path / "missing.txt"),
                retry=RetryConfig(max_attempts=1),
                timeout_seconds=1,
            ),
            TaskConfig(
                task_id="existing-file",
                task_type="file_exists",
                target=str(existing_file),
                retry=RetryConfig(max_attempts=1),
                timeout_seconds=1,
            ),
        ]
    )

    assert len(results) == 2
    assert results[0].status == TaskStatus.FAILED
    assert results[1].status == TaskStatus.SUCCESS


def test_summary_reflects_attempts_and_retries(tmp_path: Path):
    """Verify summary includes status counts and retry attempts."""
    logger.info("Testing executor summary with retry statistics")

    existing_file = tmp_path / "exists.txt"
    existing_file.write_text("ok", encoding="utf-8")

    executor = TaskExecutor(parent_logger=setup_logging(stdout=False))
    executor.run_all(
        [
            TaskConfig(
                task_id="existing-file",
                task_type="file_exists",
                target=str(existing_file),
                retry=RetryConfig(max_attempts=1),
                timeout_seconds=1,
            ),
            TaskConfig(
                task_id="missing-file",
                task_type="file_exists",
                target=str(tmp_path / "missing.txt"),
                retry=RetryConfig(
                    max_attempts=2,
                    base_delay_seconds=0,
                    max_delay_seconds=0,
                    jitter_seconds=0,
                ),
                timeout_seconds=1,
            ),
        ]
    )

    summary = executor.summary()

    assert summary["total"] == 2
    assert summary["by_status"]["success"] == 1
    assert summary["by_status"]["failed"] == 1
    assert summary["total_attempts"] == 3
    assert summary["retried_tasks"] == 1


def test_execute_with_timeout_raises_typed_timeout():
    """Verify internal timeout path raises TaskTimeoutError."""
    logger.info("Testing internal timeout exception type")

    executor = TaskExecutor(parent_logger=setup_logging(stdout=False))

    with pytest.raises(TaskTimeoutError):
        executor._execute_with_timeout(
            TaskConfig(
                task_id="internal-timeout",
                task_type="sleep",
                target="local",
                params={"duration_seconds": 0.2},
                retry=RetryConfig(max_attempts=1),
                timeout_seconds=0.01,
            )
        )


def test_http_check_validation_rejects_bad_method():
    """Verify HTTP task validation rejects unsupported methods."""
    logger.info("Testing HTTP method validation")

    executor = TaskExecutor(parent_logger=setup_logging(stdout=False))

    result = executor.run_task(
        TaskConfig(
            task_id="bad-http-method",
            task_type="http_check",
            target="https://www.python.org",
            params={"method": "TRACE", "expected_status": 200},
            retry=RetryConfig(max_attempts=1),
            timeout_seconds=1,
        )
    )

    assert result.status == TaskStatus.FAILED
    assert "unsupported HTTP method" in result.error_message


def test_runtime_validation_rejects_invalid_task_specific_result():
    """Verify task-specific validation failures surface as failed task results."""
    logger.info("Testing task-specific validation failure path")

    executor = TaskExecutor(parent_logger=setup_logging(stdout=False))

    result = executor.run_task(
        TaskConfig(
            task_id="empty-file-target",
            task_type="file_exists",
            target="",
            retry=RetryConfig(max_attempts=1),
            timeout_seconds=1,
        )
    )

    assert result.status == TaskStatus.FAILED
    assert "target path must not be empty" in result.error_message
