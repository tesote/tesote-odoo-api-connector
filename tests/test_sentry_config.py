# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tests for Sentry error tracking configuration.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestSentryConfig:
    """Test Sentry configuration and filtering."""

    def test_decode_dsn(self):
        """Test that DSN can be decoded from base64."""
        from utils.sentry_config import _decode_dsn

        dsn = _decode_dsn()
        assert dsn is not None
        assert dsn.startswith("https://")
        assert "sentry.io" in dsn

    def test_decode_dsn_format(self):
        """Test that decoded DSN has correct format."""
        from utils.sentry_config import _decode_dsn

        dsn = _decode_dsn()
        # DSN format: https://{public_key}@{host}/{project_id}
        assert dsn.count("@") == 1
        assert dsn.count("/") >= 3

    def test_init_sentry_success(self):
        """Test successful Sentry initialization."""
        with patch("sentry_sdk.init") as mock_init:
            from utils.sentry_config import init_sentry

            result = init_sentry()

            assert result is True
            mock_init.assert_called_once()

            # Check that init was called with correct parameters
            call_kwargs = mock_init.call_args[1]
            assert "dsn" in call_kwargs
            assert "before_send" in call_kwargs
            assert call_kwargs["environment"] == "production"
            assert call_kwargs["send_default_pii"] is True
            assert call_kwargs["release"] == "tesote_connector@18.0.1.0.0"

    def test_init_sentry_import_error(self):
        """Test Sentry initialization when SDK is not installed."""
        # Temporarily remove sentry_sdk from sys.modules
        import sys

        original_sentry = sys.modules.get("sentry_sdk")
        if "sentry_sdk" in sys.modules:
            del sys.modules["sentry_sdk"]

        try:
            # Mock the import to raise ImportError
            with patch.dict("sys.modules", {"sentry_sdk": None}):
                from utils.sentry_config import _configure_sentry_for_odoo

                result = _configure_sentry_for_odoo("fake_dsn")

                # Should return False but not raise exception
                assert result is False
        finally:
            # Restore original state
            if original_sentry:
                sys.modules["sentry_sdk"] = original_sentry

    def test_should_capture_event_from_tesote_module(self):
        """Test that events from tesote_connector are captured."""
        from utils.sentry_config import _should_capture_event

        # Create a fake exception with traceback from our module
        try:
            # Simulate raising an error from our module
            raise ValueError("Test error from tesote_connector")
        except ValueError:
            exc_info = sys.exc_info()

        # Mock the hint with exception info
        hint = {"exc_info": exc_info}
        event = {"exception": {"values": []}}

        # Patch traceback.extract_tb to return frames from our module
        with patch("traceback.extract_tb") as mock_extract:
            mock_frame = MagicMock()
            mock_frame.filename = "/path/to/tesote_connector/models/tesote_backend.py"
            mock_frame.lineno = 123
            mock_extract.return_value = [mock_frame]

            result = _should_capture_event(event, hint)

        # Event should be captured (not None)
        assert result is not None
        assert result == event

    def test_should_capture_event_from_other_module(self):
        """Test that events from other modules are dropped."""
        from utils.sentry_config import _should_capture_event

        # Create a fake exception
        try:
            raise ValueError("Test error from other module")
        except ValueError:
            exc_info = sys.exc_info()

        hint = {"exc_info": exc_info}
        event = {"exception": {"values": []}}

        # Patch traceback.extract_tb to return frames from another module
        with patch("traceback.extract_tb") as mock_extract:
            mock_frame = MagicMock()
            mock_frame.filename = "/path/to/odoo/addons/other_module/models/some_model.py"
            mock_frame.lineno = 456
            mock_extract.return_value = [mock_frame]

            result = _should_capture_event(event, hint)

        # Event should be dropped (None)
        assert result is None

    def test_should_capture_event_with_stacktrace(self):
        """Test event filtering using stacktrace in event dict."""
        from utils.sentry_config import _should_capture_event

        # Event with stacktrace containing tesote_connector frame
        event = {
            "exception": {
                "values": [
                    {
                        "stacktrace": {
                            "frames": [
                                {"filename": "/odoo/addons/base/models/ir_model.py"},
                                {"filename": "/odoo/addons/tesote_connector/components/adapter.py"},
                            ]
                        }
                    }
                ]
            }
        }
        hint = {}

        result = _should_capture_event(event, hint)

        # Should be captured because one frame is from tesote_connector
        assert result is not None
        assert result == event

    def test_should_capture_event_no_tesote_frames(self):
        """Test that events without tesote_connector frames are dropped."""
        from utils.sentry_config import _should_capture_event

        # Event with stacktrace not containing tesote_connector
        event = {
            "exception": {
                "values": [
                    {
                        "stacktrace": {
                            "frames": [
                                {"filename": "/odoo/addons/base/models/ir_model.py"},
                                {"filename": "/odoo/addons/sale/models/sale_order.py"},
                            ]
                        }
                    }
                ]
            }
        }
        hint = {}

        result = _should_capture_event(event, hint)

        # Should be dropped
        assert result is None

    def test_capture_exception_success(self):
        """Test manual exception capture."""
        with patch("sentry_sdk.capture_exception") as mock_capture:
            from utils.sentry_config import capture_exception

            test_exception = ValueError("Test exception")
            capture_exception(test_exception, level="error", tags={"test": "value"})

            mock_capture.assert_called_once_with(
                test_exception, level="error", tags={"test": "value"}
            )

    def test_capture_exception_import_error(self):
        """Test exception capture when Sentry is not available."""
        import sys

        original_sentry = sys.modules.get("sentry_sdk")
        if "sentry_sdk" in sys.modules:
            del sys.modules["sentry_sdk"]

        try:
            with patch.dict("sys.modules", {"sentry_sdk": None}):
                # Re-import to get the version without sentry_sdk
                import importlib

                import utils.sentry_config

                importlib.reload(utils.sentry_config)

                test_exception = ValueError("Test exception")

                # Should not raise exception
                utils.sentry_config.capture_exception(test_exception)
        finally:
            if original_sentry:
                sys.modules["sentry_sdk"] = original_sentry

    def test_capture_message_success(self):
        """Test manual message capture."""
        with patch("sentry_sdk.capture_message") as mock_capture:
            from utils.sentry_config import capture_message

            capture_message("Test message", level="info", tags={"operation": "sync"})

            mock_capture.assert_called_once_with(
                "Test message", level="info", tags={"operation": "sync"}
            )

    def test_capture_message_import_error(self):
        """Test message capture when Sentry is not available."""
        import sys

        original_sentry = sys.modules.get("sentry_sdk")
        if "sentry_sdk" in sys.modules:
            del sys.modules["sentry_sdk"]

        try:
            with patch.dict("sys.modules", {"sentry_sdk": None}):
                # Re-import to get the version without sentry_sdk
                import importlib

                import utils.sentry_config

                importlib.reload(utils.sentry_config)

                # Should not raise exception
                utils.sentry_config.capture_message("Test message")
        finally:
            if original_sentry:
                sys.modules["sentry_sdk"] = original_sentry

    def test_obfuscated_dsn_is_not_plaintext(self):
        """Test that the DSN in source code is obfuscated (base64)."""
        from utils.sentry_config import _OBFUSCATED_DSN

        # The obfuscated DSN should not contain "https://" or "sentry.io"
        assert "https://" not in _OBFUSCATED_DSN
        assert "sentry.io" not in _OBFUSCATED_DSN

        # Should be valid base64 (ends with = padding or valid base64 chars)
        import base64

        try:
            decoded = base64.b64decode(_OBFUSCATED_DSN)
            assert len(decoded) > 0
        except Exception:
            pytest.fail("_OBFUSCATED_DSN is not valid base64")

    def test_sentry_tags_include_module_info(self):
        """Test that Sentry is initialized with proper tags."""
        with patch("sentry_sdk.init") as mock_init:
            from utils.sentry_config import _configure_sentry_for_odoo

            _configure_sentry_for_odoo("https://fake@sentry.io/123")

            call_kwargs = mock_init.call_args[1]
            assert "tags" in call_kwargs
            assert call_kwargs["tags"]["module"] == "tesote_connector"
            assert call_kwargs["tags"]["odoo_version"] == "18.0"

    def test_performance_monitoring_disabled(self):
        """Test that performance monitoring is disabled (traces_sample_rate=0.0)."""
        with patch("sentry_sdk.init") as mock_init:
            from utils.sentry_config import _configure_sentry_for_odoo

            _configure_sentry_for_odoo("https://fake@sentry.io/123")

            call_kwargs = mock_init.call_args[1]
            # Performance monitoring should be disabled to reduce overhead
            assert call_kwargs["traces_sample_rate"] == 0.0
