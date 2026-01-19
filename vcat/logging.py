"""Structured logging for the VCAT package.

This module provides a configured logging setup that:

- Uses structured JSON logging for production
- Uses human-readable format for development
- Supports different log levels per module
- Includes context information (timestamps, module names)

Usage:
    >>> from vcat.logging import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Processing page", page_id="f1r", line_count=42)

Environment Variables:
    VCAT_LOG_LEVEL: Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    VCAT_LOG_FORMAT: Set format ("json" or "text", default "text")

Example:
    # Enable debug logging
    >>> import os
    >>> os.environ["VCAT_LOG_LEVEL"] = "DEBUG"
    >>> logger = get_logger("parsers")
    >>> logger.debug("Parsing locus", locus_num=1)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from collections.abc import MutableMapping
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Outputs log records as JSON objects with consistent structure
    for easy parsing by log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format.

        Returns:
            JSON string representation of the log record.
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add location info
        if record.pathname:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "taskName",
                "message",
            }
        }
        if extra_fields:
            log_data["context"] = extra_fields

        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Human-readable formatter with color support.

    Uses ANSI color codes for different log levels to improve
    readability in terminal output.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True) -> None:
        """Initialize ColoredFormatter.

        Args:
            use_colors: Whether to use ANSI color codes.
        """
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.use_colors = use_colors and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors.

        Args:
            record: Log record to format.

        Returns:
            Formatted string with optional color codes.
        """
        # Format base message
        message = super().format(record)

        # Add extra context fields if present
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "taskName",
                "message",
                "asctime",
            }
        }
        if extra_fields:
            context_str = " | " + " ".join(f"{k}={v!r}" for k, v in extra_fields.items())
            message += context_str

        # Add colors
        if self.use_colors:
            color = self.COLORS.get(record.levelname, "")
            message = f"{color}{message}{self.RESET}"

        return message


class ContextAdapter(logging.LoggerAdapter):
    """Logger adapter that supports structured context.

    Allows passing keyword arguments to log methods which are
    included as extra fields in the log record.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing", page_id="f1r", count=42)
    """

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        """Process log message and add context.

        Args:
            msg: Log message.
            kwargs: Keyword arguments including 'extra' context.

        Returns:
            Tuple of (message, updated kwargs).
        """
        # Extract extra fields from kwargs
        extra = kwargs.get("extra", {})

        # Move any non-standard kwargs to extra
        standard_keys = {"exc_info", "stack_info", "stacklevel", "extra"}
        for key in list(kwargs.keys()):
            if key not in standard_keys:
                extra[key] = kwargs.pop(key)

        # Merge with adapter's extra
        extra.update(self.extra or {})
        kwargs["extra"] = extra

        return msg, kwargs


# Module-level logger cache
_loggers: dict[str, ContextAdapter] = {}


def get_logger(name: str | None = None) -> ContextAdapter:
    """Get a configured logger instance.

    Returns a logger with structured logging support. The logger
    format and level can be configured via environment variables.

    Args:
        name: Logger name (typically __name__). If None, returns
            the root VCAT logger.

    Returns:
        Configured logger adapter with context support.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing complete", records=100)
    """
    if name is None:
        name = "vcat"

    # Return cached logger if exists
    if name in _loggers:
        return _loggers[name]

    # Get configuration from environment
    log_level = os.environ.get("VCAT_LOG_LEVEL", "INFO").upper()
    log_format = os.environ.get("VCAT_LOG_FORMAT", "text").lower()

    # Create logger
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, log_level, logging.INFO))

        # Create handler
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logger.level)

        # Set formatter based on configuration
        if log_format == "json":
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(ColoredFormatter())

        logger.addHandler(handler)

        # Prevent propagation to root logger
        logger.propagate = False

    # Wrap in adapter for context support
    adapter = ContextAdapter(logger, {})
    _loggers[name] = adapter

    return adapter


def configure_logging(
    level: str = "INFO",
    format: str = "text",
    stream: Any = None,
) -> None:
    """Configure logging for the entire VCAT package.

    This is typically called once at application startup to
    configure all VCAT loggers.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format: Log format ("json" or "text").
        stream: Output stream (default: sys.stderr).

    Example:
        >>> configure_logging(level="DEBUG", format="json")
    """
    # Clear cached loggers
    _loggers.clear()

    # Set environment variables for subsequent get_logger calls
    os.environ["VCAT_LOG_LEVEL"] = level.upper()
    os.environ["VCAT_LOG_FORMAT"] = format.lower()

    # Configure root vcat logger
    root_logger = logging.getLogger("vcat")
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Create handler
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(root_logger.level)

    # Set formatter
    if format.lower() == "json":
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(ColoredFormatter())

    root_logger.addHandler(handler)
    root_logger.propagate = False


# Convenience function for quick debug logging
def log_debug(msg: str, **kwargs: Any) -> None:
    """Log a debug message with context.

    Convenience function for quick debug logging without
    needing to get a logger first.

    Args:
        msg: Log message.
        **kwargs: Context fields to include.
    """
    get_logger("vcat.debug").debug(msg, **kwargs)
