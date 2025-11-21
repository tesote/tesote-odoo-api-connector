# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Unified Colored Console Logger for tesote_connector.

Provides consolidated logging with:
- Colored console output (enabled in dev or with TESOTE_DEBUG=true)
- Always-on error console output (ERROR/CRITICAL always visible)
- Automatic Sentry error capture (production only, not in development)
- Singleton pattern to prevent duplicate handlers
- Emoji support for log levels
"""

import hashlib
import logging
import os
import sys
import time

# Make this module importable both as utils.colored_logger and as a standalone
__all__ = ["get_logger", "is_debug_enabled", "is_development_mode", "is_sentry_initialized"]


# Global registry to track configured loggers (singleton pattern)
_configured_loggers = set()


def is_development_mode() -> bool:
    """
    Check if running in development mode.

    Development mode is detected if:
    - ODOO_ENV is set to 'development' or 'dev'
    - Odoo's config.get('dev_mode') is True

    Returns:
        bool: True if in development mode
    """
    try:
        from odoo.tools import config

        dev_mode = config.get("dev_mode")
        # Handle MagicMock in tests - only True if explicitly True
        if dev_mode is True:
            return True
    except (ImportError, KeyError, AttributeError, Exception):
        pass

    odoo_env = os.environ.get("ODOO_ENV", "production").lower()
    return odoo_env in ("development", "dev")


def is_debug_enabled() -> bool:
    """
    Check if debug mode is enabled for colored logs.

    Debug mode (colored logs) enabled if:
    - ODOO_ENV is 'development' or 'dev', OR
    - TESOTE_DEBUG is set to 'true', '1', or 'yes'

    Returns:
        bool: True if debug mode enabled
    """
    # Check TESOTE_DEBUG first (can override production mode)
    tesote_debug = os.environ.get("TESOTE_DEBUG", "").lower()
    if tesote_debug in ("true", "1", "yes"):
        return True

    # Fall back to development mode check
    return is_development_mode()


def is_sentry_initialized() -> bool:
    """
    Check if Sentry SDK is initialized and ready.

    Returns:
        bool: True if Sentry is initialized and active
    """
    try:
        import sentry_sdk

        client = sentry_sdk.Hub.current.client
        return client is not None
    except (ImportError, AttributeError, Exception):
        return False


class SentryHandler(logging.Handler):
    """
    Logging handler that sends ERROR and CRITICAL messages to Sentry.

    Only active in production mode - disabled in development to avoid noise.
    Implements duplicate prevention to avoid sending same error multiple times.
    """

    def __init__(self):
        """Initialize SentryHandler with ERROR level and deduplication."""
        super().__init__(level=logging.ERROR)
        self._sent_events = {}  # {message_hash: timestamp}
        self._dedup_window = 300  # 5 minutes in seconds
        self._max_cache_size = 1000

    def emit(self, record: logging.LogRecord):
        """
        Emit log record to Sentry if appropriate.

        Args:
            record: Log record to emit
        """
        try:
            # IMPORTANT: Skip if in development mode (avoid noise)
            if is_development_mode():
                return

            # Check if Sentry is initialized
            if not is_sentry_initialized():
                return

            # Check for duplicate within dedup window
            msg_hash = self._hash_record(record)
            if self._is_duplicate(msg_hash):
                return

            # Send to Sentry
            self._send_to_sentry(record)

            # Track as sent
            self._sent_events[msg_hash] = time.time()

            # Cleanup old entries if cache too large
            if len(self._sent_events) > self._max_cache_size:
                self._cleanup_old_events()

        except Exception:
            # Never let Sentry handler break logging
            pass

    def _hash_record(self, record: logging.LogRecord) -> str:
        """
        Create hash of record for deduplication.

        Args:
            record: Log record to hash

        Returns:
            str: Hash of record message and exception type
        """
        # Include message and exception type in hash
        hash_parts = [record.getMessage()]

        if record.exc_info:
            exc_type = record.exc_info[0]
            if exc_type:
                hash_parts.append(str(exc_type.__name__))

        hash_string = "|".join(hash_parts)
        return hashlib.md5(hash_string.encode()).hexdigest()

    def _is_duplicate(self, msg_hash: str) -> bool:
        """
        Check if message was recently sent.

        Args:
            msg_hash: Hash of message to check

        Returns:
            bool: True if duplicate within dedup window
        """
        if msg_hash not in self._sent_events:
            return False

        # Check if within dedup window
        last_sent = self._sent_events[msg_hash]
        return (time.time() - last_sent) < self._dedup_window

    def _cleanup_old_events(self):
        """Remove events older than dedup window from cache."""
        now = time.time()
        self._sent_events = {
            k: v for k, v in self._sent_events.items() if (now - v) < self._dedup_window
        }

    def _send_to_sentry(self, record: logging.LogRecord):
        """
        Send log record to Sentry.

        Args:
            record: Log record to send
        """
        try:
            import sentry_sdk

            # If exc_info present, capture as exception
            if record.exc_info:
                sentry_sdk.capture_exception(
                    record.exc_info,
                    level=self._map_level(record.levelno),
                    extras=self._extract_extras(record),
                )
            else:
                # Otherwise capture as message
                sentry_sdk.capture_message(
                    record.getMessage(),
                    level=self._map_level(record.levelno),
                    extras=self._extract_extras(record),
                )
        except Exception:
            # Fail silently
            pass

    def _map_level(self, levelno: int) -> str:
        """
        Map logging level to Sentry level.

        Args:
            levelno: Python logging level number

        Returns:
            str: Sentry level string
        """
        if levelno >= logging.CRITICAL:
            return "fatal"
        elif levelno >= logging.ERROR:
            return "error"
        elif levelno >= logging.WARNING:
            return "warning"
        elif levelno >= logging.INFO:
            return "info"
        else:
            return "debug"

    def _extract_extras(self, record: logging.LogRecord) -> dict:
        """
        Extract extra context from log record.

        Args:
            record: Log record

        Returns:
            dict: Extra context for Sentry
        """
        extras = {}

        # Include standard record attributes
        extras["module"] = record.module
        extras["function"] = record.funcName
        extras["line_number"] = record.lineno

        # Include any extra attributes passed via extra= parameter
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                extras[key] = value

        return extras


def get_logger(name: str, category: str | None = None) -> logging.Logger:
    """
    Get unified logger with colored console output and Sentry integration.

    This is the main entry point for all logging in tesote_connector.
    Replaces logging.getLogger(__name__) throughout the codebase.

    Features:
    - Colored console output (when debug mode enabled)
    - Always-on error console handler (ERROR/CRITICAL always visible)
    - Automatic Sentry error capture (production only)
    - Singleton pattern (no duplicate handlers)
    - Emoji support for log levels

    Args:
        name: Logger name (usually __name__)
        category: Optional category for organization (http, sync, webhook)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        from utils.colored_logger import get_logger
        _logger = get_logger(__name__, category='http')
        _logger.info("✅ Request successful")
        _logger.error("❌ Request failed", exc_info=True)  # Auto-sent to Sentry
    """
    logger = logging.getLogger(name)

    # Singleton pattern - only configure once
    if name in _configured_loggers:
        return logger

    # Mark as configured
    _configured_loggers.add(name)

    # Set base level to DEBUG (handlers control what's actually shown)
    logger.setLevel(logging.DEBUG)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    # 1. Conditional colored console handler (all levels, only in debug mode)
    if is_debug_enabled():
        try:
            import colorlog

            colored_formatter = colorlog.ColoredFormatter(
                fmt="%(log_color)s%(levelname)-8s%(reset)s %(blue)s[%(name)s]%(reset)s %(message)s",
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

            colored_handler = colorlog.StreamHandler(sys.stdout)
            colored_handler.setLevel(logging.DEBUG)
            colored_handler.setFormatter(colored_formatter)
            logger.addHandler(colored_handler)

        except ImportError:
            # Fallback to standard logging if colorlog unavailable
            standard_formatter = logging.Formatter(
                fmt="%(levelname)-8s [%(name)s] %(message)s",
                datefmt=None,
            )
            standard_handler = logging.StreamHandler(sys.stdout)
            standard_handler.setLevel(logging.DEBUG)
            standard_handler.setFormatter(standard_formatter)
            logger.addHandler(standard_handler)

    # 2. Always-on error console handler (ERROR/CRITICAL, always enabled)
    error_formatter = logging.Formatter(
        fmt="%(levelname)-8s [%(name)s] %(message)s",
        datefmt=None,
    )
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

    # 3. Sentry handler (ERROR/CRITICAL, only in production)
    if is_sentry_initialized() and not is_development_mode():
        sentry_handler = SentryHandler()
        logger.addHandler(sentry_handler)

    return logger


# Backward compatibility helpers
def setup_colored_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Legacy function for backward compatibility.

    Use get_logger() instead for new code.

    Args:
        name: Logger name
        level: Logging level (ignored, logger uses DEBUG)

    Returns:
        logging.Logger: Configured logger
    """
    return get_logger(name)


def get_http_logger() -> logging.Logger:
    """Get logger for HTTP requests with 'http' category."""
    return get_logger("tesote.http", category="http")


def get_sync_logger() -> logging.Logger:
    """Get logger for sync operations with 'sync' category."""
    return get_logger("tesote.sync", category="sync")


def get_webhook_logger() -> logging.Logger:
    """Get logger for webhook operations with 'webhook' category."""
    return get_logger("tesote.webhook", category="webhook")
