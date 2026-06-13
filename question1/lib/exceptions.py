from __future__ import annotations

import logging


logger = logging.getLogger("config_resolver.exceptions")


class ConfigResolverError(Exception):
    """Base exception for config resolver errors."""

    def __init__(self, message: str):
        """Initialize resolver error with validation and logging."""
        if not message or not message.strip():
            logger.error("ConfigResolverError initialized with empty message")
            raise ValueError("Exception message must not be empty")

        logger.debug("Initializing ConfigResolverError: %s", message)
        super().__init__(message)


class ConfigFileNotFoundError(ConfigResolverError):
    """Raised when a configuration file does not exist."""

    def __init__(self, path: str):
        """Initialize missing file error."""
        if not path or not path.strip():
            logger.error("ConfigFileNotFoundError initialized with empty path")
            raise ValueError("path must not be empty")

        message = f"Configuration file does not exist: {path}"
        logger.error(message)
        super().__init__(message)
        self.path = path


class InvalidConfigError(ConfigResolverError):
    """Raised when configuration structure or syntax is invalid."""

    def __init__(self, message: str, source: str | None = None):
        """Initialize invalid config error."""
        full_message = f"{message} (source={source})" if source else message
        logger.error("Invalid configuration: %s", full_message)
        super().__init__(full_message)
        self.source = source


class EnvironmentOverrideError(ConfigResolverError):
    """Raised when environment variable overrides are invalid."""

    def __init__(self, env_key: str, message: str):
        """Initialize environment override error."""
        if not env_key or not env_key.strip():
            logger.error("EnvironmentOverrideError initialized with empty env_key")
            raise ValueError("env_key must not be empty")

        full_message = f"Invalid environment override {env_key}: {message}"
        logger.error(full_message)
        super().__init__(full_message)
        self.env_key = env_key


class MergeConflictError(ConfigResolverError):
    """Raised when incompatible configuration values are detected."""

    def __init__(self, path: str, message: str):
        """Initialize merge conflict error."""
        if not path or not path.strip():
            logger.error("MergeConflictError initialized with empty path")
            raise ValueError("path must not be empty")

        full_message = f"Merge conflict at {path}: {message}"
        logger.error(full_message)
        super().__init__(full_message)
        self.path = path


class UnsupportedFormatError(ConfigResolverError):
    """Raised when config file format is unsupported."""

    def __init__(self, suffix: str):
        """Initialize unsupported format error."""
        if suffix is None:
            logger.error("UnsupportedFormatError initialized with None suffix")
            raise ValueError("suffix must not be None")

        normalized_suffix = suffix.strip().lower()

        if not normalized_suffix:
            logger.error("UnsupportedFormatError initialized with empty suffix")
            raise ValueError("suffix must not be empty")

        message = f"Unsupported config format: {normalized_suffix}"
        logger.error(message)
        super().__init__(message)
        self.suffix = normalized_suffix
