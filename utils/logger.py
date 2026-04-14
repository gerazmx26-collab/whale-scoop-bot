"""Logging utilities for Whale Scoop Bot."""

import logging
import sys
from datetime import datetime


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup logger with terminal output and tags."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler with custom format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Format: [TAG] message
    formatter = logging.Formatter(
        "[%(label)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    # Create label filter for tags
    class TagFilter(logging.Filter):
        def filter(self, record):
            if hasattr(record, 'label'):
                return True
            # Default label
            record.label = "DATA"
            return True

    handler.addFilter(TagFilter())

    return logger


class TaggedLogger:
    """Logger wrapper with tag support."""

    TAGS = {
        "DATA": "[DATA]",
        "SIGNAL": "[SIGNAL]",
        "RISK": "[RISK]",
        "EXECUTION": "[EXECUTION]",
    }

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def _log(self, level: int, tag: str, message: str):
        """Log with tag."""
        extra = {"label": tag}
        self.logger.log(level, message, extra=extra)

    def debug(self, tag: str, message: str):
        self._log(logging.DEBUG, tag, message)

    def info(self, tag: str, message: str):
        self._log(logging.INFO, tag, message)

    def warning(self, tag: str, message: str):
        self._log(logging.WARNING, tag, message)

    def error(self, tag: str, message: str):
        self._log(logging.ERROR, tag, message)