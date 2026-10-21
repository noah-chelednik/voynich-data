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
from collections.abc import MutableMapping
from datetime import UTC, datetime
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

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
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

# The package's logging configuration (B-060): the stream given to configure_logging, and the
# loggers outside the "vcat" hierarchy that get_logger has given their own handler. Loggers named
# "vcat" or "vcat.<child>" have no handler of their own: they pass their records to "vcat", whose
# handler and level configure_logging sets, so a child obeys the package configuration.
_PACKAGE = "vcat"
_stream: Any = None
_independent: set[str] = set()


def _in_package(name: str) -> bool:
    return name == _PACKAGE or name.startswith(_PACKAGE + ".")


def _install_handler(logger: logging.Logger) -> None:
    """Give the logger one handler on the configured stream, at the configured level and format."""
    level = getattr(logging, os.environ.get("VCAT_LOG_LEVEL", "INFO").upper(), logging.INFO)
    log_format = os.environ.get("VCAT_LOG_FORMAT", "text").lower()
    logger.handlers.clear()
    logger.setLevel(level)
    handler = logging.StreamHandler(_stream or sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(StructuredFormatter() if log_format == "json" else ColoredFormatter())
    logger.addHandler(handler)
    # Prevent propagation to the Python root logger
    logger.propagate = False


def get_logger(name: str | None = None) -> ContextAdapter:
    """Get a configured logger instance.

    Returns a logger with structured logging support. A logger named "vcat" or "vcat.<child>"
    writes through the package logger "vcat" (its stream, level and format, as configure_logging
    or the environment set them); any other name gets its own handler, configured the same way.

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
        name = _PACKAGE

    # Return cached logger if exists
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    if _in_package(name):
        package = logging.getLogger(_PACKAGE)
        if not package.handlers:
            _install_handler(package)
        if name != _PACKAGE:
            # No handler and no level of its own: the package logger decides (B-060)
            logger.handlers.clear()
            logger.setLevel(logging.NOTSET)
            logger.propagate = True
    elif not logger.handlers:
        _install_handler(logger)
        _independent.add(name)

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

    Sets the level, format and stream of the package logger "vcat" (which every "vcat.<child>"
    logger writes through) and of every other logger get_logger has configured.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format: Log format ("json" or "text").
        stream: Output stream (default: sys.stderr).

    Example:
        >>> configure_logging(level="DEBUG", format="json")
    """
    global _stream

    # Clear cached loggers
    _loggers.clear()

    # Set environment variables for subsequent get_logger calls
    os.environ["VCAT_LOG_LEVEL"] = level.upper()
    os.environ["VCAT_LOG_FORMAT"] = format.lower()
    _stream = stream

    _install_handler(logging.getLogger(_PACKAGE))
    for name in sorted(_independent):
        _install_handler(logging.getLogger(name))


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
