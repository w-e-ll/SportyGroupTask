from __future__ import annotations

import abc
import logging
from typing import Callable

from question2.lib.exceptions import DuplicateTaskTypeError, TaskValidationError, UnknownTaskTypeError
from question2.lib.models import TaskConfig


logger = logging.getLogger("task_executor.registry")


class BaseTask(abc.ABC):
    """Abstract base class for all executable task types."""

    def __init__(self, config: TaskConfig, parent_logger: logging.Logger):
        """Initialize task with config and task-aware logger adapter."""
        logger.debug("Initializing task instance: task_id=%s task_type=%s", config.task_id, config.task_type)

        self.config = config
        self.logger = logging.LoggerAdapter(
            parent_logger,
            {"task_id": config.task_id},
        )

        logger.debug("Task instance initialized: task_id=%s", config.task_id)

    @abc.abstractmethod
    def execute(self) -> dict:
        """Execute task and return task-specific result data."""

    def validate(self) -> bool:
        """Validate task-specific runtime requirements."""
        self.logger.debug("Running default task validation")
        return True


_task_registry: dict[str, type[BaseTask]] = {}


def register_task(task_type: str) -> Callable[[type[BaseTask]], type[BaseTask]]:
    """Register a task implementation class for a task type."""
    logger.debug("Preparing task registration: task_type=%s", task_type)

    if not task_type or not task_type.strip():
        logger.error("Cannot register task with empty task_type")
        raise ValueError("task_type must not be empty")

    normalized_task_type = task_type.strip()

    def decorator(cls: type[BaseTask]) -> type[BaseTask]:
        """Register decorated task class in the global task registry."""
        logger.debug(
            "Registering task class: task_type=%s class=%s",
            normalized_task_type,
            cls.__name__,
        )

        if not issubclass(cls, BaseTask):
            logger.error(
                "Task registration failed: class=%s is not BaseTask subclass",
                cls.__name__,
            )
            raise TypeError("registered task class must inherit from BaseTask")

        if normalized_task_type in _task_registry:
            logger.error("Duplicate task registration attempted: task_type=%s", normalized_task_type)
            raise DuplicateTaskTypeError(normalized_task_type)

        _task_registry[normalized_task_type] = cls

        logger.info(
            "Task type registered: task_type=%s class=%s",
            normalized_task_type,
            cls.__name__,
        )

        return cls

    return decorator


def get_task_class(task_type: str) -> type[BaseTask]:
    """Return registered task class for a task type."""
    logger.debug("Resolving task class: task_type=%s", task_type)

    if not task_type or not task_type.strip():
        logger.error("Cannot resolve empty task_type")
        raise TaskValidationError("unknown", "task_type must not be empty")

    normalized_task_type = task_type.strip()

    try:
        task_class = _task_registry[normalized_task_type]
    except KeyError as exc:
        logger.error("Unknown task type requested: task_type=%s", normalized_task_type)
        raise UnknownTaskTypeError(normalized_task_type) from exc

    logger.debug(
        "Resolved task class: task_type=%s class=%s",
        normalized_task_type,
        task_class.__name__,
    )

    return task_class


def registered_task_types() -> list[str]:
    """Return sorted list of currently registered task types."""
    logger.debug("Listing registered task types")
    return sorted(_task_registry.keys())
