from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


logger = logging.getLogger("task_executor.models")


class TaskStatus(Enum):
    """Supported task execution statuses."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class RetryConfig:
    """Retry settings for a single task."""

    max_attempts: int = 1
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 2.0
    jitter_seconds: float = 0.1

    def __post_init__(self) -> None:
        """Validate retry configuration after initialization."""
        logger.debug("Validating RetryConfig: %s", self)

        if self.max_attempts < 1:
            logger.error("Invalid max_attempts=%s", self.max_attempts)
            raise ValueError("max_attempts must be >= 1")

        if self.base_delay_seconds < 0:
            logger.error("Invalid base_delay_seconds=%s", self.base_delay_seconds)
            raise ValueError("base_delay_seconds must be >= 0")

        if self.max_delay_seconds < self.base_delay_seconds:
            logger.error(
                "Invalid max_delay_seconds=%s lower than base_delay_seconds=%s",
                self.max_delay_seconds,
                self.base_delay_seconds,
            )
            raise ValueError("max_delay_seconds must be >= base_delay_seconds")

        if self.jitter_seconds < 0:
            logger.error("Invalid jitter_seconds=%s", self.jitter_seconds)
            raise ValueError("jitter_seconds must be >= 0")

        logger.debug("RetryConfig validation completed")


@dataclass(frozen=True)
class TaskConfig:
    """Configuration for a single executable task."""

    task_id: str
    task_type: str
    target: str
    params: dict[str, Any] = field(default_factory=dict)
    retry: RetryConfig = field(default_factory=RetryConfig)
    timeout_seconds: float | None = 10.0

    def __post_init__(self) -> None:
        """Validate task configuration after initialization."""
        logger.debug("Validating TaskConfig for task_id=%s", self.task_id)

        if not self.task_id.strip():
            logger.error("TaskConfig validation failed: empty task_id")
            raise ValueError("task_id must not be empty")

        if not self.task_type.strip():
            logger.error("TaskConfig validation failed for task_id=%s: empty task_type", self.task_id)
            raise ValueError("task_type must not be empty")

        if not isinstance(self.params, dict):
            logger.error("TaskConfig validation failed for task_id=%s: params is not dict", self.task_id)
            raise TypeError("params must be a dictionary")

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            logger.error(
                "TaskConfig validation failed for task_id=%s: timeout_seconds=%s",
                self.task_id,
                self.timeout_seconds,
            )
            raise ValueError("timeout_seconds must be positive or None")

        logger.debug("TaskConfig validation completed for task_id=%s", self.task_id)


@dataclass(frozen=True)
class TaskResult:
    """Result produced after executing a task."""

    task_id: str
    status: TaskStatus
    started_at: datetime
    completed_at: datetime | None = None
    result_data: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    attempts: int = 1

    def __post_init__(self) -> None:
        """Validate task result after initialization."""
        logger.debug("Validating TaskResult for task_id=%s status=%s", self.task_id, self.status.value)

        if not self.task_id.strip():
            logger.error("TaskResult validation failed: empty task_id")
            raise ValueError("task_id must not be empty")

        if self.attempts < 1:
            logger.error("TaskResult validation failed for task_id=%s: attempts=%s", self.task_id, self.attempts)
            raise ValueError("attempts must be >= 1")

        if self.status in {TaskStatus.FAILED, TaskStatus.TIMEOUT} and not self.error_message:
            logger.warning(
                "TaskResult for task_id=%s has failure status without error_message",
                self.task_id,
            )

        logger.debug("TaskResult validation completed for task_id=%s", self.task_id)
