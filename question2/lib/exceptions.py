from __future__ import annotations

import logging


logger = logging.getLogger("task_executor.exceptions")


class TaskExecutorError(Exception):
    """Base exception for task executor errors."""

    def __init__(self, message: str):
        """Initialize executor error with validation and logging."""
        if not message or not message.strip():
            logger.error("TaskExecutorError initialized with empty message")
            raise ValueError("Exception message must not be empty")

        logger.debug("Initializing TaskExecutorError: %s", message)
        super().__init__(message)


class TaskValidationError(TaskExecutorError):
    """Raised when task configuration or task validation fails."""

    def __init__(self, task_id: str, message: str):
        """Initialize validation error for a specific task."""
        if not task_id or not task_id.strip():
            logger.error("TaskValidationError initialized with empty task_id")
            raise ValueError("task_id must not be empty")

        full_message = f"Task validation failed for task_id={task_id}: {message}"
        logger.error(full_message)
        super().__init__(full_message)
        self.task_id = task_id


class TaskTimeoutError(TaskExecutorError, TimeoutError):
    """Raised when a task exceeds its configured timeout."""

    def __init__(self, task_id: str, timeout_seconds: float | None):
        """Initialize timeout error for a specific task."""
        if not task_id or not task_id.strip():
            logger.error("TaskTimeoutError initialized with empty task_id")
            raise ValueError("task_id must not be empty")

        message = f"Task exceeded timeout for task_id={task_id}, timeout_seconds={timeout_seconds}"
        logger.error(message)
        super().__init__(message)
        self.task_id = task_id
        self.timeout_seconds = timeout_seconds


class UnknownTaskTypeError(TaskExecutorError):
    """Raised when a task type is not registered."""

    def __init__(self, task_type: str):
        """Initialize unknown task type error."""
        if not task_type or not task_type.strip():
            logger.error("UnknownTaskTypeError initialized with empty task_type")
            raise ValueError("task_type must not be empty")

        message = f"Unknown task type: {task_type}"
        logger.error(message)
        super().__init__(message)
        self.task_type = task_type


class DuplicateTaskTypeError(TaskExecutorError):
    """Raised when trying to register the same task type twice."""

    def __init__(self, task_type: str):
        """Initialize duplicate task type error."""
        if not task_type or not task_type.strip():
            logger.error("DuplicateTaskTypeError initialized with empty task_type")
            raise ValueError("task_type must not be empty")

        message = f"Task type already registered: {task_type}"
        logger.error(message)
        super().__init__(message)
        self.task_type = task_type
