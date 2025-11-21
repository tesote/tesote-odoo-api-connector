# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Colored Logger Utility for Development.
Provides enhanced logging with colors for better readability.
"""

import logging
import os


def setup_colored_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Setup a colored logger for development.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: INFO)

    Returns:
        Configured logger with colored output
    """
    logger = logging.getLogger(name)

    # Only setup if not already configured
    if logger.handlers:
        return logger

    # Check if we're in development mode
    is_dev = os.environ.get("ODOO_ENV", "production").lower() in ["development", "dev"]

    try:
        import colorlog

        # Create colored formatter
        formatter = colorlog.ColoredFormatter(
            fmt="%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
            secondary_log_colors={},
            style="%",
        )

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level if is_dev else logging.INFO)

    except ImportError:
        # Fallback to standard logging if colorlog not available
        formatter = logging.Formatter(
            fmt="%(levelname)-8s %(name)s %(message)s",
            datefmt=None,
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger


def get_http_logger() -> logging.Logger:
    """Get a logger specifically for HTTP requests with enhanced formatting."""
    return setup_colored_logger("tesote.http", level=logging.DEBUG)


def get_sync_logger() -> logging.Logger:
    """Get a logger specifically for sync operations."""
    return setup_colored_logger("tesote.sync", level=logging.DEBUG)


def get_webhook_logger() -> logging.Logger:
    """Get a logger specifically for webhook operations."""
    return setup_colored_logger("tesote.webhook", level=logging.DEBUG)
