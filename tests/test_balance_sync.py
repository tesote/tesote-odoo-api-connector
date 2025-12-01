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
        account.odoo_account_id.id = 10

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

        # Default mock for _get_odoo_account_balance (returns 800.0 by default)
        account._get_odoo_account_balance = Mock(return_value=800.0)

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
        mock_account._get_odoo_account_balance = Mock(return_value=1000.0)
        mock_account.sync_balance_to_odoo = TesoteAccount.sync_balance_to_odoo.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account.sync_balance_to_odoo()

        assert result is False

    def test_sync_balance_skips_small_difference(self, mock_account):
        """Test that sync is skipped for differences smaller than 0.01."""
        from models.tesote_account import TesoteAccount

        mock_account.balance = 1000.005
        mock_account._get_odoo_account_balance = Mock(return_value=1000.0)
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
        mock_account._get_odoo_account_balance = Mock(return_value=1000.0)

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
        mock_account._get_odoo_account_balance = Mock(return_value=1000.0)

        mock_move = Mock()
        mock_account._create_balance_adjustment = Mock(return_value=mock_move)

        mock_account.sync_balance_to_odoo = TesoteAccount.sync_balance_to_odoo.__get__(
            mock_account, TesoteAccount
        )

        result = mock_account.sync_balance_to_odoo()

        mock_account._create_balance_adjustment.assert_called_once_with(-200.0)
        assert result == mock_move


class TestGetOdooAccountBalance:
    """Test _get_odoo_account_balance functionality."""

    def test_get_odoo_account_balance_method_exists(self):
        """Test that _get_odoo_account_balance method exists on account model."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "_get_odoo_account_balance")
        assert callable(TesoteAccount._get_odoo_account_balance)

    def test_returns_zero_when_no_odoo_account(self):
        """Test that method returns 0.0 when odoo_account_id is not set."""
        from models.tesote_account import TesoteAccount

        account = Mock(spec=TesoteAccount)
        account.ensure_one = Mock()
        account.odoo_account_id = False

        account._get_odoo_account_balance = TesoteAccount._get_odoo_account_balance.__get__(
            account, TesoteAccount
        )

        result = account._get_odoo_account_balance()

        assert result == 0.0

    def test_calculates_balance_from_move_lines(self):
        """Test that balance is calculated from account.move.line entries."""
        from models.tesote_account import TesoteAccount

        account = Mock(spec=TesoteAccount)
        account.ensure_one = Mock()
        account.odoo_account_id = Mock(id=10)

        # Mock the read_group result
        move_line_model = MagicMock()
        move_line_model.read_group = Mock(return_value=[{"debit": 1500.0, "credit": 500.0}])
        account.env = MagicMock()
        account.env.__getitem__ = Mock(return_value=move_line_model)

        account._get_odoo_account_balance = TesoteAccount._get_odoo_account_balance.__get__(
            account, TesoteAccount
        )

        result = account._get_odoo_account_balance()

        # Balance = debit - credit = 1500 - 500 = 1000
        assert result == 1000.0

        # Verify read_group was called with correct parameters
        move_line_model.read_group.assert_called_once()
        call_args = move_line_model.read_group.call_args
        domain = call_args[1]["domain"] if "domain" in call_args[1] else call_args[0][0]
        assert ("account_id", "=", 10) in domain
        assert ("parent_state", "=", "posted") in domain

    def test_returns_zero_when_no_move_lines(self):
        """Test that method returns 0.0 when no move lines exist."""
        from models.tesote_account import TesoteAccount

        account = Mock(spec=TesoteAccount)
        account.ensure_one = Mock()
        account.odoo_account_id = Mock(id=10)

        # Mock empty read_group result
        move_line_model = MagicMock()
        move_line_model.read_group = Mock(return_value=[])
        account.env = MagicMock()
        account.env.__getitem__ = Mock(return_value=move_line_model)

        account._get_odoo_account_balance = TesoteAccount._get_odoo_account_balance.__get__(
            account, TesoteAccount
        )

        result = account._get_odoo_account_balance()

        assert result == 0.0


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


class TestCreateBalanceAdjustment:
    """Test _create_balance_adjustment functionality."""

    @pytest.fixture
    def mock_account(self):
        """Create a mock TesoteAccount for adjustment tests."""
        from models.tesote_account import TesoteAccount

        account = Mock(spec=TesoteAccount)
        account.ensure_one = Mock()
        account.name = "Test Account"
        account.tesote_id = "acc_123"

        # Set up currencies
        usd_currency = Mock(id=1, name="USD")
        eur_currency = Mock(id=2, name="EUR")

        account.odoo_account_id = Mock()
        account.odoo_account_id.id = 10
        account.odoo_account_id.currency_id = usd_currency

        backend = Mock()
        backend.company_id = Mock(id=1, currency_id=usd_currency)
        backend.suspense_account_id = Mock(id=20)
        account.backend_id = backend

        # Mock environment using side_effect for __getitem__
        journal = Mock(id=5)
        move = Mock(name="TSADJ/2024/001")
        move.action_post = Mock()

        journal_model = MagicMock()
        journal_model.search = Mock(return_value=journal)
        move_model = MagicMock()
        move_model.create = Mock(return_value=move)

        env_mock = MagicMock()

        def env_getitem(key):
            if key == "account.journal":
                return journal_model
            if key == "account.move":
                return move_model
            return MagicMock()

        env_mock.__getitem__ = Mock(side_effect=env_getitem)
        account.env = env_mock

        # Store references for assertions
        account._test_usd_currency = usd_currency
        account._test_eur_currency = eur_currency
        account._test_move_model = move_model

        return account

    def test_creates_move_lines_without_currency_for_same_currency(self, mock_account):
        """Test that move lines don't have currency_id when same as company currency."""
        from models.tesote_account import TesoteAccount

        mock_account._create_balance_adjustment = TesoteAccount._create_balance_adjustment.__get__(
            mock_account, TesoteAccount
        )
        mock_account._get_adjustment_journal = TesoteAccount._get_adjustment_journal.__get__(
            mock_account, TesoteAccount
        )

        mock_account._create_balance_adjustment(100.0)

        # Get the create call arguments
        create_call = mock_account._test_move_model.create.call_args[0][0]
        lines = create_call["line_ids"]

        # Bank line should NOT have currency_id (same currency as company)
        bank_line = lines[0][2]
        assert "currency_id" not in bank_line
        assert "amount_currency" not in bank_line

    def test_creates_move_lines_with_currency_for_different_currency(self, mock_account):
        """Test that move lines have currency_id when different from company currency."""
        from models.tesote_account import TesoteAccount

        # Set bank account to use EUR (different from company USD)
        mock_account.odoo_account_id.currency_id = mock_account._test_eur_currency

        mock_account._create_balance_adjustment = TesoteAccount._create_balance_adjustment.__get__(
            mock_account, TesoteAccount
        )
        mock_account._get_adjustment_journal = TesoteAccount._get_adjustment_journal.__get__(
            mock_account, TesoteAccount
        )

        mock_account._create_balance_adjustment(100.0)

        # Get the create call arguments
        create_call = mock_account._test_move_model.create.call_args[0][0]
        lines = create_call["line_ids"]

        # Bank line should have currency_id and amount_currency
        bank_line = lines[0][2]
        assert bank_line["currency_id"] == 2  # EUR id
        assert bank_line["amount_currency"] == 100.0

        # Suspense line should NOT have currency_id (company currency)
        suspense_line = lines[1][2]
        assert "currency_id" not in suspense_line


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
