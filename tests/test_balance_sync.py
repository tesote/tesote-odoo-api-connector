# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Test Tesote balance sync functionality.
Tests the sync_balance_to_odoo() method and related journal entry creation.
"""

import inspect
from unittest.mock import MagicMock, Mock

import pytest


class TestBalanceSyncFields:
    """Test that balance sync fields exist on models."""

    def test_backend_has_suspense_account_field(self):
        """Test that backend model has suspense_account_id field."""
        from models.tesote_backend import TesoteBackend

        assert hasattr(TesoteBackend, "suspense_account_id")

    def test_account_has_odoo_account_field(self):
        """Test that account model has odoo_account_id field."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "odoo_account_id")


class TestBalanceSyncMethods:
    """Test balance sync method existence."""

    def test_sync_balance_to_odoo_method_exists(self):
        """Test that sync_balance_to_odoo method exists on account model."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "sync_balance_to_odoo")
        assert callable(TesoteAccount.sync_balance_to_odoo)

    def test_create_balance_adjustment_method_exists(self):
        """Test that _create_balance_adjustment method exists."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "_create_balance_adjustment")
        assert callable(TesoteAccount._create_balance_adjustment)

    def test_get_adjustment_journal_method_exists(self):
        """Test that _get_adjustment_journal method exists."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "_get_adjustment_journal")
        assert callable(TesoteAccount._get_adjustment_journal)


class TestSyncBalanceToOdoo:
    """Test sync_balance_to_odoo functionality."""

    @pytest.fixture
    def mock_account(self):
        """Create a mock TesoteAccount with proper attributes."""
        from models.tesote_account import TesoteAccount

        account = Mock(spec=TesoteAccount)
        account.ensure_one = Mock()
        account.name = "Test Account"
        account.tesote_id = "acc_123"
        account.balance = 1000.0
        account.odoo_account_id = Mock()
        account.odoo_account_id.current_balance = 800.0

        # Set up matching currencies to pass currency validation
        usd_currency = Mock(id=1, name="USD")
        account.currency_id = usd_currency
        account.odoo_account_id.currency_id = usd_currency
        account.odoo_account_id.company_id = Mock(currency_id=usd_currency)

        backend = Mock()
        backend.suspense_account_id = Mock()
        backend.company_id = Mock(id=1)
        account.backend_id = backend

        account.env = MagicMock()
        return account

    def test_sync_balance_skips_unmapped_account(self, mock_account):
        """Test that sync is skipped when account is not mapped to Odoo."""
        from models.tesote_account import TesoteAccount

        mock_account.odoo_account_id = False
        mock_account.sync_balance_to_odoo = TesoteAccount.sync_balance_to_odoo.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account.sync_balance_to_odoo()

        assert result is False

    def test_sync_balance_skips_without_suspense_account(self, mock_account):
        """Test that sync is skipped when suspense account not configured."""
        from models.tesote_account import TesoteAccount

        mock_account.backend_id.suspense_account_id = False
        mock_account.sync_balance_to_odoo = TesoteAccount.sync_balance_to_odoo.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account.sync_balance_to_odoo()

        assert result is False

    def test_sync_balance_skips_when_balances_match(self, mock_account):
        """Test that sync is skipped when balances are equal."""
        from models.tesote_account import TesoteAccount

        mock_account.balance = 1000.0
        mock_account.odoo_account_id.current_balance = 1000.0
        mock_account.sync_balance_to_odoo = TesoteAccount.sync_balance_to_odoo.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account.sync_balance_to_odoo()

        assert result is False

    def test_sync_balance_skips_small_difference(self, mock_account):
        """Test that sync is skipped for differences smaller than 0.01."""
        from models.tesote_account import TesoteAccount

        mock_account.balance = 1000.005
        mock_account.odoo_account_id.current_balance = 1000.0
        mock_account.sync_balance_to_odoo = TesoteAccount.sync_balance_to_odoo.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account.sync_balance_to_odoo()

        assert result is False

    def test_sync_balance_skips_currency_mismatch(self, mock_account):
        """Test that sync is skipped when currencies don't match."""
        from models.tesote_account import TesoteAccount

        # Set up different currencies
        eur_currency = Mock(id=2, name="EUR")
        mock_account.currency_id = eur_currency  # Tesote account in EUR

        mock_account.sync_balance_to_odoo = TesoteAccount.sync_balance_to_odoo.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account.sync_balance_to_odoo()

        assert result is False

    def test_sync_balance_creates_adjustment_for_positive_diff(self, mock_account):
        """Test that adjustment is created when Tesote > Odoo balance."""
        from models.tesote_account import TesoteAccount

        mock_account.balance = 1200.0
        mock_account.odoo_account_id.current_balance = 1000.0

        mock_move = Mock()
        mock_account._create_balance_adjustment = Mock(return_value=mock_move)

        mock_account.sync_balance_to_odoo = TesoteAccount.sync_balance_to_odoo.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account.sync_balance_to_odoo()

        mock_account._create_balance_adjustment.assert_called_once_with(200.0)
        assert result == mock_move

    def test_sync_balance_creates_adjustment_for_negative_diff(self, mock_account):
        """Test that adjustment is created when Tesote < Odoo balance."""
        from models.tesote_account import TesoteAccount

        mock_account.balance = 800.0
        mock_account.odoo_account_id.current_balance = 1000.0

        mock_move = Mock()
        mock_account._create_balance_adjustment = Mock(return_value=mock_move)

        mock_account.sync_balance_to_odoo = TesoteAccount.sync_balance_to_odoo.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account.sync_balance_to_odoo()

        mock_account._create_balance_adjustment.assert_called_once_with(-200.0)
        assert result == mock_move


class TestGetAdjustmentJournal:
    """Test _get_adjustment_journal functionality."""

    @pytest.fixture
    def mock_account(self):
        """Create a mock TesoteAccount."""
        from models.tesote_account import TesoteAccount

        account = Mock(spec=TesoteAccount)

        backend = Mock()
        backend.company_id = Mock(id=1)
        account.backend_id = backend

        account.env = MagicMock()

        return account

    def test_returns_existing_journal(self, mock_account):
        """Test that existing TSADJ journal is returned."""
        from models.tesote_account import TesoteAccount

        existing_journal = Mock(id=5, code="TSADJ")
        journal_model = MagicMock()
        journal_model.search = Mock(return_value=existing_journal)
        mock_account.env.__getitem__ = Mock(return_value=journal_model)

        mock_account._get_adjustment_journal = TesoteAccount._get_adjustment_journal.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account._get_adjustment_journal()

        journal_model.search.assert_called_once()
        search_domain = journal_model.search.call_args[0][0]

        # Check search criteria
        assert ("type", "=", "general") in search_domain
        assert ("code", "=", "TSADJ") in search_domain

        assert result == existing_journal

    def test_creates_journal_if_not_exists(self, mock_account):
        """Test that new TSADJ journal is created if not exists."""
        from models.tesote_account import TesoteAccount

        new_journal = Mock(id=10, code="TSADJ", name="Tesote Adjustments")
        journal_model = MagicMock()
        # Return empty recordset (falsy)
        empty_recordset = Mock()
        empty_recordset.__bool__ = Mock(return_value=False)
        journal_model.search = Mock(return_value=empty_recordset)
        journal_model.create = Mock(return_value=new_journal)
        mock_account.env.__getitem__ = Mock(return_value=journal_model)

        mock_account._get_adjustment_journal = TesoteAccount._get_adjustment_journal.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account._get_adjustment_journal()

        # Verify search was attempted
        journal_model.search.assert_called_once()

        # Verify create was called with correct values
        journal_model.create.assert_called_once()
        create_vals = journal_model.create.call_args[0][0]

        assert create_vals["name"] == "Tesote Adjustments"
        assert create_vals["code"] == "TSADJ"
        assert create_vals["type"] == "general"
        assert create_vals["company_id"] == 1

        assert result == new_journal


class TestBalanceSyncIntegration:
    """Test balance sync integration with import flow."""

    def test_import_accounts_background_calls_balance_sync(self):
        """Test that _import_accounts_background syncs balances."""
        from models.tesote_backend import TesoteBackend

        # Verify the method exists and has balance sync logic
        source = inspect.getsource(TesoteBackend._import_accounts_background)

        # Check that balance sync is mentioned in the method
        assert "sync_balance_to_odoo" in source
        assert "suspense_account_id" in source
        assert "balance_adjustments" in source
