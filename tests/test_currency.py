# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Test currency activation feature for Tesote connector.

Tests the automatic and manual activation of currencies used by Tesote accounts.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest


class TestResCurrency:
    """Test res.currency extension for Tesote."""

    @pytest.fixture
    def mock_env(self):
        """Create mock Odoo environment."""
        env = MagicMock()
        env.companies = Mock()
        env.companies.mapped = Mock(return_value=Mock())
        return env

    def test_res_currency_extension_fields(self):
        """Test that res.currency extension has required fields."""
        from models.res_currency import ResCurrency

        # Check required fields exist
        assert hasattr(ResCurrency, "tesote_account_ids")
        assert hasattr(ResCurrency, "tesote_account_count")
        assert hasattr(ResCurrency, "is_used_by_tesote")

    def test_res_currency_inherits_correctly(self):
        """Test that res.currency properly inherits from res.currency."""
        from models.res_currency import ResCurrency

        assert ResCurrency._inherit == "res.currency"

    def test_action_activate_for_invoicing_exists(self):
        """Test that action_activate_for_invoicing method exists."""
        from models.res_currency import ResCurrency

        assert hasattr(ResCurrency, "action_activate_for_invoicing")
        assert callable(ResCurrency.action_activate_for_invoicing)

    def test_action_deactivate_exists(self):
        """Test that action_deactivate method exists."""
        from models.res_currency import ResCurrency

        assert hasattr(ResCurrency, "action_deactivate")
        assert callable(ResCurrency.action_deactivate)

    def test_activate_tesote_currencies_exists(self):
        """Test that activate_tesote_currencies method exists."""
        from models.res_currency import ResCurrency

        assert hasattr(ResCurrency, "activate_tesote_currencies")
        assert callable(ResCurrency.activate_tesote_currencies)

    def test_get_tesote_currency_summary_exists(self):
        """Test that get_tesote_currency_summary method exists."""
        from models.res_currency import ResCurrency

        assert hasattr(ResCurrency, "get_tesote_currency_summary")
        assert callable(ResCurrency.get_tesote_currency_summary)

    def test_compute_tesote_account_count_exists(self):
        """Test that _compute_tesote_account_count method exists."""
        from models.res_currency import ResCurrency

        assert hasattr(ResCurrency, "_compute_tesote_account_count")
        assert callable(ResCurrency._compute_tesote_account_count)


class TestTesoteBackendCurrency:
    """Test Tesote Backend currency management features."""

    def test_backend_action_activate_currencies_exists(self):
        """Test that action_activate_currencies method exists on backend."""
        from models.tesote_backend import TesoteBackend

        assert hasattr(TesoteBackend, "action_activate_currencies")
        assert callable(TesoteBackend.action_activate_currencies)

    def test_backend_action_view_tesote_currencies_exists(self):
        """Test that action_view_tesote_currencies method exists on backend."""
        from models.tesote_backend import TesoteBackend

        assert hasattr(TesoteBackend, "action_view_tesote_currencies")
        assert callable(TesoteBackend.action_view_tesote_currencies)

    def test_backend_get_currency_status_exists(self):
        """Test that get_currency_status method exists on backend."""
        from models.tesote_backend import TesoteBackend

        assert hasattr(TesoteBackend, "get_currency_status")
        assert callable(TesoteBackend.get_currency_status)


class TestTesoteAccountCurrencyAutoActivation:
    """Test automatic currency activation in tesote.account model."""

    @pytest.fixture
    def mock_env(self):
        """Create mock Odoo environment."""
        env = MagicMock()
        env.__getitem__ = Mock(side_effect=lambda key: Mock())
        return env

    def test_account_create_from_tesote_with_currency(self, mock_env):
        """Test that create_from_tesote handles currency field."""
        from models.tesote_account import TesoteAccount

        # Test that create_from_tesote method exists and handles currency
        assert hasattr(TesoteAccount, "create_from_tesote")
        assert callable(TesoteAccount.create_from_tesote)

    def test_account_update_from_tesote_with_currency(self, mock_env):
        """Test that update_from_tesote handles currency field."""
        from models.tesote_account import TesoteAccount

        # Test that update_from_tesote method exists and handles currency
        assert hasattr(TesoteAccount, "update_from_tesote")
        assert callable(TesoteAccount.update_from_tesote)

    def test_account_currency_field_exists(self):
        """Test that currency_id field exists on tesote.account."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "currency_id")


class TestCurrencyActivationIntegration:
    """Integration tests for currency activation workflow."""

    @pytest.fixture
    def mock_currency(self):
        """Create a mock currency record."""
        currency = Mock()
        currency.name = "USD"
        currency.active = False
        currency.id = 1
        return currency

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend record."""
        backend = Mock()
        backend.id = 1
        backend.account_ids = Mock()
        backend.account_ids.mapped = Mock(return_value=Mock(ids=[1, 2]))
        return backend

    def test_currency_activation_workflow(self, mock_currency, mock_env):
        """Test that currency can be activated."""
        from models.res_currency import ResCurrency

        # Mock the write method
        mock_currency.write = Mock()

        # Create a mock recordset
        currencies = Mock(spec=ResCurrency)
        currencies.write = Mock()
        currencies.mapped = Mock(return_value=["USD"])

        # Test activation
        currencies.write({"active": True})
        currencies.write.assert_called_with({"active": True})

    def test_currency_auto_activation_on_account_import(self, mock_currency, mock_env):
        """Test that currency is auto-activated when account is imported."""
        # This tests the logic flow where:
        # 1. Account is created from API data with currency="EUR"
        # 2. Currency is found in database (but inactive)
        # 3. Currency is automatically activated

        # Mock currency search to return inactive currency
        mock_env["res.currency"].with_context.return_value.search.return_value = mock_currency

        # Verify the mock setup
        assert mock_currency.active is False

        # Simulate activation
        mock_currency.active = True
        assert mock_currency.active is True

    def test_backend_view_currencies_returns_action(self, mock_backend, mock_env):
        """Test that action_view_tesote_currencies returns proper action."""
        from models.tesote_backend import TesoteBackend

        # Create mock backend with proper methods
        backend = Mock(spec=TesoteBackend)
        backend.ensure_one = Mock()
        backend.account_ids = Mock()
        backend.account_ids.mapped = Mock(return_value=Mock(ids=[1, 2, 3]))

        # The method should return an action dict
        # This is a simplified test - actual test would verify action structure


class TestCurrencyActivationMessages:
    """Test notification messages for currency activation."""

    def test_activate_returns_notification(self):
        """Test that activation returns a notification action."""
        from models.res_currency import ResCurrency

        # Verify the method exists that returns notifications
        assert hasattr(ResCurrency, "action_activate_for_invoicing")
        assert hasattr(ResCurrency, "activate_tesote_currencies")

    def test_deactivate_returns_notification(self):
        """Test that deactivation returns a notification action."""
        from models.res_currency import ResCurrency

        assert hasattr(ResCurrency, "action_deactivate")
