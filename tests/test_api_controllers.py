"""
Tests for API controllers.
"""

import hashlib
import hmac
import unittest
from unittest.mock import MagicMock, patch


class TestBaseApiController(unittest.TestCase):
    """Test base API controller authentication."""

    def setUp(self):
        """Set up test fixtures."""
        self.env = MagicMock()
        self.backend = MagicMock()
        self.backend.id = 1
        self.backend.name = "Test Backend"

        self.webhook_config = MagicMock()
        self.webhook_config.secret_key = "test_secret_key"

    def test_verify_api_key_valid(self):
        """Test valid API key verification."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()

        # Mock request
        mock_request = MagicMock()
        mock_request.httprequest.path = "/api/accounting_accounts"
        mock_request.httprequest.query_string = b""

        timestamp = "1234567890"
        signed_payload = f"{timestamp}./api/accounting_accounts."
        signature = hmac.new(
            b"test_secret_key", signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        mock_request.httprequest.headers = {
            "X-Tesote-Signature": signature,
            "X-Tesote-Timestamp": timestamp,
        }

        with patch("controllers.api.base_controller.request", mock_request):
            controller._get_webhook_config = MagicMock(return_value=self.webhook_config)

            is_valid, error_message = controller._verify_api_key()

            self.assertTrue(is_valid)
            self.assertIsNone(error_message)

    def test_verify_api_key_invalid_signature(self):
        """Test invalid API signature verification."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()

        # Mock request
        mock_request = MagicMock()
        mock_request.httprequest.path = "/api/accounting_accounts"
        mock_request.httprequest.query_string = b""
        mock_request.httprequest.headers = {
            "X-Tesote-Signature": "invalid_signature",
            "X-Tesote-Timestamp": "1234567890",
        }

        with patch("controllers.api.base_controller.request", mock_request):
            controller._get_webhook_config = MagicMock(return_value=self.webhook_config)

            is_valid, error_message = controller._verify_api_key()

            self.assertFalse(is_valid)
            self.assertEqual(error_message, "Invalid signature")

    def test_verify_api_key_missing_headers(self):
        """Test API verification with missing headers."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()

        # Mock request with missing headers
        mock_request = MagicMock()
        mock_request.httprequest.headers = {}

        with patch("controllers.api.base_controller.request", mock_request):
            is_valid, error_message = controller._verify_api_key()

            self.assertFalse(is_valid)
            self.assertEqual(error_message, "Missing authentication headers")

    def test_verify_api_key_missing_signature_only(self):
        """Test API verification with missing signature header."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()

        mock_request = MagicMock()
        mock_request.httprequest.headers = {
            "X-Tesote-Timestamp": "1234567890",
        }

        with patch("controllers.api.base_controller.request", mock_request):
            is_valid, error_message = controller._verify_api_key()

            self.assertFalse(is_valid)
            self.assertEqual(error_message, "Missing authentication headers")

    def test_verify_api_key_no_webhook_config(self):
        """Test API verification without webhook configuration."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()

        mock_request = MagicMock()
        mock_request.httprequest.headers = {
            "X-Tesote-Signature": "some_signature",
            "X-Tesote-Timestamp": "1234567890",
        }

        with patch("controllers.api.base_controller.request", mock_request):
            controller._get_webhook_config = MagicMock(return_value=None)

            is_valid, error_message = controller._verify_api_key()

            self.assertFalse(is_valid)
            self.assertEqual(error_message, "API not configured")

    def test_verify_api_key_no_secret_key(self):
        """Test API verification with webhook config but no secret key."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()

        webhook_config_no_secret = MagicMock()
        webhook_config_no_secret.secret_key = None

        mock_request = MagicMock()
        mock_request.httprequest.headers = {
            "X-Tesote-Signature": "some_signature",
            "X-Tesote-Timestamp": "1234567890",
        }

        with patch("controllers.api.base_controller.request", mock_request):
            controller._get_webhook_config = MagicMock(return_value=webhook_config_no_secret)

            is_valid, error_message = controller._verify_api_key()

            self.assertFalse(is_valid)
            self.assertEqual(error_message, "API not configured")

    def test_verify_api_key_with_query_string(self):
        """Test valid API key verification with query parameters."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()

        mock_request = MagicMock()
        mock_request.httprequest.path = "/api/accounting_accounts"
        mock_request.httprequest.query_string = b"limit=10&offset=0"

        timestamp = "1234567890"
        signed_payload = f"{timestamp}./api/accounting_accounts.limit=10&offset=0"
        signature = hmac.new(
            b"test_secret_key", signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        mock_request.httprequest.headers = {
            "X-Tesote-Signature": signature,
            "X-Tesote-Timestamp": timestamp,
        }

        with patch("controllers.api.base_controller.request", mock_request):
            controller._get_webhook_config = MagicMock(return_value=self.webhook_config)

            is_valid, error_message = controller._verify_api_key()

            self.assertTrue(is_valid)
            self.assertIsNone(error_message)

    def test_authenticate_request_success(self):
        """Test successful authentication flow."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()
        controller._verify_api_key = MagicMock(return_value=(True, None))

        is_authenticated, error_response = controller._authenticate_request()

        self.assertTrue(is_authenticated)
        self.assertIsNone(error_response)

    def test_authenticate_request_failure(self):
        """Test failed authentication flow."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()
        controller._verify_api_key = MagicMock(return_value=(False, "Invalid signature"))

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_request.make_response = MagicMock(return_value=mock_response)

        with patch("controllers.api.base_controller.request", mock_request):
            is_authenticated, error_response = controller._authenticate_request()

            self.assertFalse(is_authenticated)
            self.assertEqual(error_response, mock_response)
            mock_request.make_response.assert_called_once()

    def test_json_response(self):
        """Test JSON response creation."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_request.make_response = MagicMock(return_value=mock_response)

        with patch("controllers.api.base_controller.request", mock_request):
            response = controller._json_response({"test": "data"}, status=200)

            self.assertEqual(response, mock_response)
            mock_request.make_response.assert_called_once()
            call_args = mock_request.make_response.call_args
            self.assertIn('"test": "data"', call_args[0][0])
            self.assertEqual(call_args[1]["status"], 200)

    def test_get_webhook_config_with_backend(self):
        """Test getting webhook config when backend exists."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()

        mock_request = MagicMock()
        mock_backend = MagicMock()
        mock_backend.id = 1
        mock_request.env = {
            "tesote.backend": MagicMock(),
            "tesote.webhook.config": MagicMock(),
        }
        mock_request.env["tesote.backend"].sudo.return_value.search.return_value = mock_backend
        mock_request.env[
            "tesote.webhook.config"
        ].sudo.return_value.search.return_value = self.webhook_config

        with patch("controllers.api.base_controller.request", mock_request):
            config = controller._get_webhook_config()

            self.assertEqual(config, self.webhook_config)

    def test_get_webhook_config_no_backend(self):
        """Test getting webhook config when no backend exists."""
        from controllers.api.base_controller import BaseApiController

        controller = BaseApiController()

        mock_request = MagicMock()
        mock_request.env = {"tesote.backend": MagicMock()}
        mock_request.env["tesote.backend"].sudo.return_value.search.return_value = None

        with patch("controllers.api.base_controller.request", mock_request):
            config = controller._get_webhook_config()

            self.assertIsNone(config)


class TestAccountingAccountController(unittest.TestCase):
    """Test accounting account API controller."""

    def setUp(self):
        """Set up test fixtures."""
        self.env = MagicMock()

        # Mock accounting account
        self.mock_account = MagicMock()
        self.mock_account.id = 1
        self.mock_account.code = "1000"
        self.mock_account.name = "Cash"
        self.mock_account.account_type = "asset_cash"
        self.mock_account.currency_id = MagicMock()
        self.mock_account.currency_id.id = 1
        self.mock_account.currency_id.name = "USD"
        self.mock_account.company_id = MagicMock()
        self.mock_account.company_id.id = 1
        self.mock_account.company_id.name = "Test Company"
        self.mock_account.reconcile = False
        self.mock_account.deprecated = False
        self.mock_account.exists = MagicMock(return_value=True)

    def test_index_authenticated(self):
        """Test index endpoint with valid authentication."""
        from controllers.api.accounting_account_controller import AccountingAccountController

        controller = AccountingAccountController()

        mock_request = MagicMock()
        mock_request.env = {"account.account": MagicMock()}
        mock_request.env["account.account"].sudo.return_value.search.return_value = [
            self.mock_account
        ]

        with (
            patch("controllers.api.accounting_account_controller.request", mock_request),
            patch("controllers.api.base_controller.request", mock_request),
        ):
            controller._authenticate_request = MagicMock(return_value=(True, None))

            controller.index()

            controller._authenticate_request.assert_called_once()
            mock_request.make_response.assert_called_once()
            # Verify the response contains the account data
            call_args = mock_request.make_response.call_args
            self.assertIn("accounting_accounts", call_args[0][0])
            self.assertEqual(call_args[1]["status"], 200)

    def test_index_unauthenticated(self):
        """Test index endpoint without authentication."""
        from controllers.api.accounting_account_controller import AccountingAccountController

        controller = AccountingAccountController()

        mock_error_response = MagicMock()
        controller._authenticate_request = MagicMock(return_value=(False, mock_error_response))

        response = controller.index()

        self.assertEqual(response, mock_error_response)

    def test_show_authenticated(self):
        """Test show endpoint with valid authentication."""
        from controllers.api.accounting_account_controller import AccountingAccountController

        controller = AccountingAccountController()

        mock_request = MagicMock()
        mock_request.env = {"account.account": MagicMock()}
        mock_request.env[
            "account.account"
        ].sudo.return_value.browse.return_value = self.mock_account

        with (
            patch("controllers.api.accounting_account_controller.request", mock_request),
            patch("controllers.api.base_controller.request", mock_request),
        ):
            controller._authenticate_request = MagicMock(return_value=(True, None))

            controller.show(1)

            controller._authenticate_request.assert_called_once()
            mock_request.make_response.assert_called_once()
            # Verify the response contains the account data
            call_args = mock_request.make_response.call_args
            self.assertIn("accounting_account", call_args[0][0])
            self.assertEqual(call_args[1]["status"], 200)

    def test_show_unauthenticated(self):
        """Test show endpoint without authentication."""
        from controllers.api.accounting_account_controller import AccountingAccountController

        controller = AccountingAccountController()

        mock_error_response = MagicMock()
        controller._authenticate_request = MagicMock(return_value=(False, mock_error_response))

        response = controller.show(1)

        self.assertEqual(response, mock_error_response)

    def test_show_not_found(self):
        """Test show endpoint when account not found."""
        from controllers.api.accounting_account_controller import AccountingAccountController

        controller = AccountingAccountController()

        mock_request = MagicMock()

        mock_account_not_found = MagicMock()
        mock_account_not_found.exists = MagicMock(return_value=False)

        mock_request.env = {"account.account": MagicMock()}
        mock_request.env[
            "account.account"
        ].sudo.return_value.browse.return_value = mock_account_not_found

        with (
            patch("controllers.api.accounting_account_controller.request", mock_request),
            patch("controllers.api.base_controller.request", mock_request),
        ):
            controller._authenticate_request = MagicMock(return_value=(True, None))

            controller.show(999)

            mock_request.make_response.assert_called_once()
            # Check that 404 response was created
            call_args = mock_request.make_response.call_args
            self.assertIn("not found", call_args[0][0])
            self.assertEqual(call_args[1]["status"], 404)

    def test_serialize_accounting_account(self):
        """Test account serialization."""
        from controllers.api.accounting_account_controller import AccountingAccountController

        controller = AccountingAccountController()

        result = controller._serialize_accounting_account(self.mock_account)

        self.assertEqual(result["id"], 1)
        self.assertEqual(result["code"], "1000")
        self.assertEqual(result["name"], "Cash")
        self.assertEqual(result["account_type"], "asset_cash")
        self.assertEqual(result["currency_id"], 1)
        self.assertEqual(result["currency_code"], "USD")
        self.assertEqual(result["company_id"], 1)
        self.assertEqual(result["company_name"], "Test Company")
        self.assertEqual(result["reconcile"], False)
        self.assertEqual(result["deprecated"], False)

    def test_serialize_accounting_account_no_currency(self):
        """Test account serialization without currency."""
        from controllers.api.accounting_account_controller import AccountingAccountController

        controller = AccountingAccountController()

        mock_account_no_currency = MagicMock()
        mock_account_no_currency.id = 2
        mock_account_no_currency.code = "2000"
        mock_account_no_currency.name = "Expenses"
        mock_account_no_currency.account_type = "expense"
        mock_account_no_currency.currency_id = None
        mock_account_no_currency.company_id = MagicMock()
        mock_account_no_currency.company_id.id = 1
        mock_account_no_currency.company_id.name = "Test Company"
        mock_account_no_currency.reconcile = False
        mock_account_no_currency.deprecated = False

        result = controller._serialize_accounting_account(mock_account_no_currency)

        self.assertIsNone(result["currency_id"])
        self.assertIsNone(result["currency_code"])

    def test_index_exception_handling(self):
        """Test index endpoint exception handling."""
        from controllers.api.accounting_account_controller import AccountingAccountController

        controller = AccountingAccountController()

        mock_request = MagicMock()
        mock_request.env = {"account.account": MagicMock()}
        mock_request.env["account.account"].sudo.return_value.search.side_effect = Exception(
            "Database error"
        )

        with (
            patch("controllers.api.accounting_account_controller.request", mock_request),
            patch("controllers.api.base_controller.request", mock_request),
            patch(
                "controllers.api.accounting_account_controller.capture_exception"
            ) as mock_capture,
        ):
            controller._authenticate_request = MagicMock(return_value=(True, None))

            controller.index()

            mock_capture.assert_called_once()
            mock_request.make_response.assert_called_once()
            # Check that 500 response was created
            call_args = mock_request.make_response.call_args
            self.assertEqual(call_args[1]["status"], 500)


if __name__ == "__main__":
    unittest.main()
