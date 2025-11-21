# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Sentry error tracking configuration for tesote_connector module.

This module initializes Sentry SDK with:
- Obfuscated DSN (base64 encoded for non-plain-text storage)
- Module-specific error filtering (only captures errors from tesote_connector)
- Odoo-specific integration settings
"""

import base64
import logging
import traceback

_logger = logging.getLogger(__name__)

_OBFUSCATED_DSN = (
    "aHR0cHM6Ly8xMDNjNzM1ODQ5M2Y2ZjlkMjA2YWQ5OWI5MDdjODllMEBvNDUwNTc4ODcyMTMz"
    "MjIyNC5pbmdlc3QudXMuc2VudHJ5LmlvLzQ1MTAzNDY5ODM3MDI1Mjg="
)


def _decode_dsn():
    """
    Decode the obfuscated DSN.

    Note: This is base64 encoding, which provides obfuscation but not security.
    It can be easily reversed but prevents plain-text exposure in source code.

    Returns:
        str: Decoded DSN string
    """
    try:
        return base64.b64decode(_OBFUSCATED_DSN).decode("utf-8")
    except Exception as e:
        _logger.error(f"Failed to decode Sentry DSN: {e}")
        return None


def _should_capture_event(event, hint):
    """
    Filter events to only capture errors from tesote_connector module.

    This callback is executed for every event before it's sent to Sentry.
    It filters out errors that don't originate from our module.

    Args:
        event (dict): Sentry event dictionary
        hint (dict): Additional context about the event

    Returns:
        dict or None: Event to send, or None to drop the event
    """
    # Check if there's an exception in the hint
    if "exc_info" in hint:
        exc_type, exc_value, exc_tb = hint["exc_info"]

        # Extract the traceback to find where the error originated
        tb_list = traceback.extract_tb(exc_tb)

        # Check if any frame in the traceback is from our module
        for frame in tb_list:
            # Check if the frame's filename contains our module paths
            if any(
                path in frame.filename
                for path in [
                    "tesote_connector",
                    "tesote-odoo-api-connector",
                ]
            ):
                # This is from our module, capture it
                _logger.debug(f"Capturing Sentry event from {frame.filename}:{frame.lineno}")
                return event

        # Error didn't originate from our module, drop it
        _logger.debug(f"Dropping non-tesote_connector error: {exc_type.__name__}")
        return None

    # If there's no exception info, check the event's stack trace
    if "exception" in event:
        for exception in event["exception"].get("values", []):
            stacktrace = exception.get("stacktrace", {})
            for frame in stacktrace.get("frames", []):
                filename = frame.get("filename", "")
                if any(
                    path in filename
                    for path in [
                        "tesote_connector",
                        "tesote-odoo-api-connector",
                    ]
                ):
                    return event

    # Default: drop the event if we can't determine it's from our module
    return None


def _configure_sentry_for_odoo(dsn):
    """
    Configure Sentry SDK with Odoo-specific settings.

    Args:
        dsn (str): Sentry DSN string

    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            # Filter events to only our module
            before_send=_should_capture_event,
            # Environment name (you can customize based on Odoo config)
            environment="production",  # Change to "staging" or "development" as needed
            # Include request data and PII for better debugging
            send_default_pii=True,
            # Sample rate for performance monitoring (0.0 to 1.0)
            # Set to 0.0 to disable performance monitoring and only track errors
            traces_sample_rate=0.0,
            # Maximum number of breadcrumbs
            max_breadcrumbs=50,
            # Attach stack traces to messages
            attach_stacktrace=True,
            # Release version (use module version)
            release="tesote_connector@18.0.1.0.0",
            # Additional tags
            tags={
                "module": "tesote_connector",
                "odoo_version": "18.0",
            },
        )

        _logger.info("Sentry SDK initialized successfully for tesote_connector")
        return True

    except ImportError:
        _logger.warning(
            "sentry-sdk not installed. Error tracking disabled. "
            "Install with: pip install sentry-sdk"
        )
        return False
    except Exception as e:
        _logger.error(f"Failed to initialize Sentry SDK: {e}")
        return False


def init_sentry():
    """
    Initialize Sentry error tracking for tesote_connector module.

    This is the main entry point for Sentry initialization.
    Call this once during module initialization.

    Returns:
        bool: True if initialization was successful, False otherwise
    """
    # Decode the DSN
    dsn = _decode_dsn()
    if not dsn:
        _logger.warning("Failed to decode Sentry DSN. Error tracking disabled.")
        return False

    # Configure Sentry
    return _configure_sentry_for_odoo(dsn)


def capture_exception(exception, **kwargs):
    """
    Manually capture an exception and send it to Sentry.

    This is a convenience wrapper around sentry_sdk.capture_exception()
    that handles cases where Sentry might not be initialized.

    Args:
        exception: The exception to capture
        **kwargs: Additional arguments to pass to sentry_sdk.capture_exception()

    Example:
        try:
            risky_operation()
        except Exception as e:
            from .utils.sentry_config import capture_exception
            capture_exception(e, level="error", tags={"operation": "sync"})
    """
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exception, **kwargs)
    except ImportError:
        # Sentry not available, just log locally
        _logger.error(f"Exception occurred (Sentry unavailable): {exception}")
    except Exception as e:
        _logger.error(f"Failed to capture exception to Sentry: {e}")


def capture_message(message, level="info", **kwargs):
    """
    Manually capture a message and send it to Sentry.

    This is a convenience wrapper around sentry_sdk.capture_message()
    that handles cases where Sentry might not be initialized.

    Args:
        message (str): The message to capture
        level (str): Severity level (debug, info, warning, error, fatal)
        **kwargs: Additional arguments to pass to sentry_sdk.capture_message()

    Example:
        from .utils.sentry_config import capture_message
        capture_message("Sync completed", level="info", tags={"accounts": 5})
    """
    try:
        import sentry_sdk

        sentry_sdk.capture_message(message, level=level, **kwargs)
    except ImportError:
        # Sentry not available, just log locally
        _logger.info(f"Message: {message} (Sentry unavailable)")
    except Exception as e:
        _logger.error(f"Failed to capture message to Sentry: {e}")
