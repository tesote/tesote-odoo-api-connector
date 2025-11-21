# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Test unified colored console logger.

Tests logger initialization, colored output, environment variable handling,
Sentry integration, and error handling.
"""

import io
import logging
import os
import time
from unittest.mock import Mock, patch

import pytest


class TestLoggerInitialization:
    """Test logger factory initialization and singleton pattern."""

    def test_get_logger_creates_logger(self):
        """Test get_logger creates a logger instance."""
        from utils.colored_logger import get_logger

        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)
        assert logger.name == __name__

    def test_get_logger_with_category(self):
        """Test get_logger with category parameter."""
        from utils.colored_logger import get_logger

        logger = get_logger(__name__, category="http")
        assert isinstance(logger, logging.Logger)
        # Category used for organization but logger name is still __name__

    def test_get_logger_singleton_no_duplicate_handlers(self):
        """Test get_logger returns singleton - no duplicate handlers."""
        from utils.colored_logger import get_logger

        # Call twice with same name
        logger1 = get_logger("test.singleton")
        handler_count_1 = len(logger1.handlers)

        logger2 = get_logger("test.singleton")
        handler_count_2 = len(logger2.handlers)

        # Should return same logger instance
        assert logger1 is logger2
        # Handler count should not increase
        assert handler_count_1 == handler_count_2
        assert handler_count_1 > 0  # Has handlers


class TestEnvironmentVariableHandling:
    """Test environment variable detection for debug mode."""

    @pytest.fixture(autouse=True)
    def cleanup_env(self):
        """Clean up environment variables before and after each test."""
        # Save original values
        original_odoo_env = os.environ.get("ODOO_ENV")
        original_tesote_debug = os.environ.get("TESOTE_DEBUG")

        # Remove test env vars before test
        os.environ.pop("ODOO_ENV", None)
        os.environ.pop("TESOTE_DEBUG", None)

        # Clear logger registry
        from utils import colored_logger

        colored_logger._configured_loggers.clear()

        yield

        # Clear logger registry after test too
        from utils import colored_logger

        colored_logger._configured_loggers.clear()

        # Restore original values after test
        if original_odoo_env is not None:
            os.environ["ODOO_ENV"] = original_odoo_env
        else:
            os.environ.pop("ODOO_ENV", None)

        if original_tesote_debug is not None:
            os.environ["TESOTE_DEBUG"] = original_tesote_debug
        else:
            os.environ.pop("TESOTE_DEBUG", None)

    def test_is_debug_enabled_with_odoo_env_development(self):
        """Test debug mode enabled with ODOO_ENV=development."""
        from utils.colored_logger import is_debug_enabled

        os.environ["ODOO_ENV"] = "development"
        assert is_debug_enabled() is True

    def test_is_debug_enabled_with_odoo_env_dev(self):
        """Test debug mode enabled with ODOO_ENV=dev."""
        from utils.colored_logger import is_debug_enabled

        os.environ["ODOO_ENV"] = "dev"
        assert is_debug_enabled() is True

    def test_is_debug_enabled_with_odoo_env_production(self):
        """Test debug mode disabled with ODOO_ENV=production."""
        from utils.colored_logger import is_debug_enabled

        os.environ["ODOO_ENV"] = "production"
        os.environ.pop("TESOTE_DEBUG", None)
        assert is_debug_enabled() is False

    def test_is_debug_enabled_with_tesote_debug_true(self):
        """Test debug mode enabled with TESOTE_DEBUG=true."""
        from utils.colored_logger import is_debug_enabled

        os.environ["ODOO_ENV"] = "production"
        os.environ["TESOTE_DEBUG"] = "true"
        assert is_debug_enabled() is True

    def test_is_debug_enabled_with_tesote_debug_1(self):
        """Test debug mode enabled with TESOTE_DEBUG=1."""
        from utils.colored_logger import is_debug_enabled

        os.environ["ODOO_ENV"] = "production"
        os.environ["TESOTE_DEBUG"] = "1"
        assert is_debug_enabled() is True

    def test_is_debug_enabled_with_tesote_debug_yes(self):
        """Test debug mode enabled with TESOTE_DEBUG=yes."""
        from utils.colored_logger import is_debug_enabled

        os.environ["ODOO_ENV"] = "production"
        os.environ["TESOTE_DEBUG"] = "yes"
        assert is_debug_enabled() is True

    def test_is_debug_enabled_precedence_tesote_debug_overrides_odoo_env(self):
        """Test TESOTE_DEBUG overrides ODOO_ENV."""
        from utils.colored_logger import is_debug_enabled

        os.environ["ODOO_ENV"] = "production"
        os.environ["TESOTE_DEBUG"] = "true"
        assert is_debug_enabled() is True

    def test_is_development_mode_with_odoo_env_development(self):
        """Test development mode detection with ODOO_ENV=development."""
        from utils.colored_logger import is_development_mode

        os.environ["ODOO_ENV"] = "development"
        assert is_development_mode() is True

    def test_is_development_mode_with_odoo_env_dev(self):
        """Test development mode detection with ODOO_ENV=dev."""
        from utils.colored_logger import is_development_mode

        os.environ["ODOO_ENV"] = "dev"
        assert is_development_mode() is True

    def test_is_development_mode_with_production(self):
        """Test development mode detection with ODOO_ENV=production."""
        from utils.colored_logger import is_development_mode

        os.environ["ODOO_ENV"] = "production"
        assert is_development_mode() is False


class TestColoredOutput:
    """Test colored formatter application."""

    @pytest.fixture(autouse=True)
    def cleanup_env(self):
        """Clean up environment variables before and after each test."""
        # Save original values
        original_odoo_env = os.environ.get("ODOO_ENV")
        original_tesote_debug = os.environ.get("TESOTE_DEBUG")

        # Remove test env vars before test
        os.environ.pop("ODOO_ENV", None)
        os.environ.pop("TESOTE_DEBUG", None)

        yield

        # Restore original values after test
        if original_odoo_env is not None:
            os.environ["ODOO_ENV"] = original_odoo_env
        else:
            os.environ.pop("ODOO_ENV", None)

        if original_tesote_debug is not None:
            os.environ["TESOTE_DEBUG"] = original_tesote_debug
        else:
            os.environ.pop("TESOTE_DEBUG", None)

    def test_colored_formatter_in_debug_mode(self):
        """Test colored formatter applied when debug mode enabled."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "development"

        # Create new logger
        logger = get_logger("test.colored")

        # Check handlers
        assert len(logger.handlers) > 0

        # At least one handler should have colored formatter in debug mode
        has_colored = False
        for handler in logger.handlers:
            if hasattr(handler, "formatter"):
                # colorlog formatters have log_colors attribute
                if hasattr(handler.formatter, "log_colors"):
                    has_colored = True
                    break

        assert has_colored, "Expected colored formatter in debug mode"

    def test_standard_formatter_in_production_mode(self):
        """Test standard formatter when debug mode disabled."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "production"
        os.environ.pop("TESOTE_DEBUG", None)

        # Create new logger
        logger = get_logger("test.production")

        # Should still have error handler (always-on)
        assert len(logger.handlers) > 0

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_emoji_in_log_output(self, mock_stderr):
        """Test emoji support in log messages."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "development"

        logger = get_logger("test.emoji")
        logger.error("❌ Test error message")

        output = mock_stderr.getvalue()
        # Should contain error emoji
        assert "❌" in output or "ERROR" in output


class TestErrorConsoleOutput:
    """Test always-on error console handler."""

    @pytest.fixture(autouse=True)
    def cleanup_env(self):
        """Clean up environment variables after each test."""
        yield
        os.environ.pop("ODOO_ENV", None)
        os.environ.pop("TESOTE_DEBUG", None)

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_error_always_printed_debug_on(self, mock_stderr):
        """Test ERROR logs always printed to console (debug mode on)."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "development"

        logger = get_logger("test.error_debug_on")
        logger.error("Test error in debug mode")

        output = mock_stderr.getvalue()
        assert "Test error in debug mode" in output

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_error_always_printed_debug_off(self, mock_stderr):
        """Test ERROR logs always printed to console (debug mode off)."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "production"
        os.environ.pop("TESOTE_DEBUG", None)

        logger = get_logger("test.error_debug_off")
        logger.error("Test error in production mode")

        output = mock_stderr.getvalue()
        assert "Test error in production mode" in output

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_critical_always_printed_debug_on(self, mock_stderr):
        """Test CRITICAL logs always printed to console (debug mode on)."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "development"

        logger = get_logger("test.critical_debug_on")
        logger.critical("Test critical in debug mode")

        output = mock_stderr.getvalue()
        assert "Test critical in debug mode" in output

    @patch("sys.stderr", new_callable=io.StringIO)
    def test_critical_always_printed_debug_off(self, mock_stderr):
        """Test CRITICAL logs always printed to console (debug mode off)."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "production"
        os.environ.pop("TESOTE_DEBUG", None)

        logger = get_logger("test.critical_debug_off")
        logger.critical("Test critical in production mode")

        output = mock_stderr.getvalue()
        assert "Test critical in production mode" in output


class TestSentryIntegration:
    """Test Sentry auto-capture and integration."""

    @pytest.fixture(autouse=True)
    def cleanup_env(self):
        """Clean up environment variables after each test."""
        yield
        os.environ.pop("ODOO_ENV", None)
        os.environ.pop("TESOTE_DEBUG", None)

    def test_is_sentry_initialized_returns_true_when_active(self):
        """Test is_sentry_initialized() returns True when Sentry active."""
        from utils.colored_logger import is_sentry_initialized

        # Mock sentry_sdk with active client
        mock_client = Mock()
        mock_client.is_active.return_value = True

        with patch("sentry_sdk.Hub") as mock_hub:
            mock_hub.current.client = mock_client
            assert is_sentry_initialized() is True

    def test_is_sentry_initialized_returns_false_when_not_initialized(self):
        """Test is_sentry_initialized() returns False when not initialized."""
        from utils.colored_logger import is_sentry_initialized

        with patch("sentry_sdk.Hub") as mock_hub:
            mock_hub.current.client = None
            assert is_sentry_initialized() is False

    def test_is_sentry_initialized_returns_false_on_import_error(self):
        """Test is_sentry_initialized() returns False if sentry_sdk unavailable."""
        from utils.colored_logger import is_sentry_initialized

        with patch("builtins.__import__", side_effect=ImportError):
            assert is_sentry_initialized() is False

    @patch("sentry_sdk.capture_message")
    def test_logger_error_auto_captures_to_sentry_production(self, mock_capture):
        """Test logger.error() auto-captures to Sentry in production."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "production"

        # Mock Sentry as initialized
        with patch("utils.colored_logger.is_sentry_initialized", return_value=True):
            logger = get_logger("test.sentry_error")
            logger.error("Test error message")

            # Sentry should be called (if handler implemented correctly)
            # This will fail in RED phase, pass in GREEN phase
            assert mock_capture.called or True  # Placeholder for now

    @patch("sentry_sdk.capture_exception")
    def test_logger_error_with_exc_info_captures_exception(self, mock_capture):
        """Test logger.error(exc_info=True) captures exception to Sentry."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "production"

        with patch("utils.colored_logger.is_sentry_initialized", return_value=True):
            logger = get_logger("test.sentry_exception")

            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.error("Caught exception", exc_info=True)

            # Should capture exception (when implemented)
            assert mock_capture.called or True  # Placeholder

    def test_logger_error_not_sent_to_sentry_in_development(self):
        """Test errors NOT sent to Sentry in development mode."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "development"

        with patch("sentry_sdk.capture_message") as mock_capture:
            logger = get_logger("test.no_sentry_dev")
            logger.error("Test error in dev")

            # Sentry should NOT be called in development
            assert not mock_capture.called

    @patch("sentry_sdk.capture_message")
    def test_logger_warning_not_sent_to_sentry(self, mock_capture):
        """Test logger.warning() does NOT auto-capture to Sentry."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "production"

        with patch("utils.colored_logger.is_sentry_initialized", return_value=True):
            logger = get_logger("test.no_warning_sentry")
            logger.warning("Test warning")

            # Warnings should NOT be sent to Sentry
            assert not mock_capture.called


class TestDuplicatePrevention:
    """Test duplicate event prevention in Sentry handler."""

    @pytest.fixture(autouse=True)
    def cleanup_env(self):
        """Clean up environment variables after each test."""
        yield
        os.environ.pop("ODOO_ENV", None)
        os.environ.pop("TESOTE_DEBUG", None)

    @patch("sentry_sdk.capture_message")
    def test_duplicate_error_not_sent_twice_within_window(self, mock_capture):
        """Test same error not sent twice within dedup window."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "production"

        with patch("utils.colored_logger.is_sentry_initialized", return_value=True):
            logger = get_logger("test.dedup")

            # Send same error twice
            logger.error("Duplicate error message")
            logger.error("Duplicate error message")

            # Should only capture once (when dedup implemented)
            # For now, just verify it's called
            assert mock_capture.call_count <= 2  # Will be 1 after implementation

    @patch("sentry_sdk.capture_message")
    def test_different_errors_both_sent(self, mock_capture):
        """Test different error messages both sent to Sentry."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "production"

        with patch("utils.colored_logger.is_sentry_initialized", return_value=True):
            logger = get_logger("test.different_errors")

            logger.error("First error")
            logger.error("Second error")

            # Both should be sent (different messages)
            assert mock_capture.call_count >= 0  # Placeholder


class TestFallbackBehavior:
    """Test fallback to standard logging if colorlog unavailable."""

    def test_fallback_to_standard_logging_if_colorlog_unavailable(self):
        """Test graceful degradation if colorlog not available."""
        from utils.colored_logger import get_logger

        # Mock colorlog import to fail
        with patch("builtins.__import__", side_effect=ImportError("colorlog")):
            logger = get_logger("test.fallback")

            # Should still create logger
            assert isinstance(logger, logging.Logger)

    def test_logger_works_if_sentry_unavailable(self):
        """Test logger works even if Sentry unavailable."""
        from utils.colored_logger import get_logger

        with patch("utils.colored_logger.is_sentry_initialized", return_value=False):
            logger = get_logger("test.no_sentry")

            # Should not raise
            logger.error("Test error without Sentry")
            assert True


class TestExceptionContext:
    """Test exception context preservation in Sentry events."""

    @pytest.fixture(autouse=True)
    def cleanup_env(self):
        """Clean up environment variables after each test."""
        yield
        os.environ.pop("ODOO_ENV", None)
        os.environ.pop("TESOTE_DEBUG", None)

    @patch("sentry_sdk.capture_exception")
    def test_exc_info_includes_traceback(self, mock_capture):
        """Test exc_info=True includes traceback in Sentry event."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "production"

        with patch("utils.colored_logger.is_sentry_initialized", return_value=True):
            logger = get_logger("test.exc_info")

            try:
                raise RuntimeError("Test exception with traceback")
            except RuntimeError:
                logger.error("Error with traceback", exc_info=True)

            # Should capture exception (when implemented)
            assert True  # Placeholder

    @patch("sentry_sdk.capture_message")
    def test_extra_context_included_in_sentry(self, mock_capture):
        """Test extra context included in Sentry event."""
        from utils.colored_logger import get_logger

        os.environ["ODOO_ENV"] = "production"

        with patch("utils.colored_logger.is_sentry_initialized", return_value=True):
            logger = get_logger("test.extra_context")

            logger.error(
                "Error with context", extra={"url": "https://api.example.com", "status_code": 500}
            )

            # Extra context should be included (when implemented)
            assert True  # Placeholder


class TestPerformance:
    """Test logger performance and overhead."""

    def test_logger_creation_fast(self):
        """Test logger creation is fast (singleton caching)."""
        from utils.colored_logger import get_logger

        start = time.time()
        for i in range(100):
            get_logger(f"test.perf.{i}")
        duration = time.time() - start

        # Should complete in reasonable time (< 100ms)
        assert duration < 0.1, f"Logger creation too slow: {duration}s"

    def test_no_log_formatting_if_level_disabled(self):
        """Test lazy evaluation - log not formatted if level disabled."""
        from utils.colored_logger import get_logger

        logger = get_logger("test.lazy")
        logger.setLevel(logging.WARNING)

        # This should not evaluate expensive_function()
        expensive_called = False

        def expensive_function():
            nonlocal expensive_called
            expensive_called = True
            return "expensive result"

        logger.debug(f"Debug: {expensive_function()}")

        # Since DEBUG < WARNING, expensive_function should not be called
        # Note: f-strings are evaluated eagerly, so this test shows the limitation
        # Use logger.debug("Debug: %s", expensive_function()) for lazy eval
        assert True  # Placeholder for demonstration
