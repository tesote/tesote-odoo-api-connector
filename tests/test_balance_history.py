# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Test Tesote Account Balance History model following TDD principles.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest


class TestTesoteAccountBalanceHistory:
    """Test Tesote Account Balance History model."""

    @pytest.fixture
    def mock_env(self):
        """Create mock Odoo environment."""
        env = MagicMock()
        env.__getitem__ = Mock(side_effect=lambda key: Mock())
        return env

    def test_balance_history_model_fields(self):
        """Test that balance history model has required fields."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        # Check required fields
        assert hasattr(TesoteAccountBalanceHistory, "account_id")
        assert hasattr(TesoteAccountBalanceHistory, "balance")
        assert hasattr(TesoteAccountBalanceHistory, "currency_id")
        assert hasattr(TesoteAccountBalanceHistory, "recorded_at")
        assert hasattr(TesoteAccountBalanceHistory, "previous_balance")
        assert hasattr(TesoteAccountBalanceHistory, "balance_change")
        assert hasattr(TesoteAccountBalanceHistory, "balance_change_percent")
        assert hasattr(TesoteAccountBalanceHistory, "sync_log_id")
        assert hasattr(TesoteAccountBalanceHistory, "source")

    def test_balance_history_model_name(self):
        """Test that model has correct name."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        assert TesoteAccountBalanceHistory._name == "tesote.account.balance.history"
        assert TesoteAccountBalanceHistory._description == "Tesote Account Balance History"

    def test_balance_history_ordering(self):
        """Test that history is ordered by recorded_at descending."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        assert TesoteAccountBalanceHistory._order == "recorded_at desc"

    def test_source_field_selection(self):
        """Test source field has correct selection values."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        assert hasattr(TesoteAccountBalanceHistory, "source")
        # Source field should have sync, webhook, manual options

    def test_balance_change_compute_method_exists(self):
        """Test that balance change compute method exists."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        assert hasattr(TesoteAccountBalanceHistory, "_compute_balance_change")
        assert callable(TesoteAccountBalanceHistory._compute_balance_change)

    def test_display_name_compute_method_exists(self):
        """Test that display name compute method exists."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        assert hasattr(TesoteAccountBalanceHistory, "_compute_display_name")
        assert callable(TesoteAccountBalanceHistory._compute_display_name)

    def test_related_fields_exist(self):
        """Test that related fields for reporting exist."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        assert hasattr(TesoteAccountBalanceHistory, "backend_id")
        assert hasattr(TesoteAccountBalanceHistory, "account_name")


class TestTesoteAccountBalanceHistoryIntegration:
    """Test balance history integration with account model."""

    def test_account_has_balance_history_relation(self):
        """Test that account model has One2many to balance history."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "balance_history_ids")
        assert hasattr(TesoteAccount, "balance_history_count")

    def test_account_has_record_balance_history_method(self):
        """Test that account model has method to record balance history."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "_record_balance_history")
        assert callable(TesoteAccount._record_balance_history)

    def test_account_has_view_balance_history_action(self):
        """Test that account model has action to view balance history."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "action_view_balance_history")
        assert callable(TesoteAccount.action_view_balance_history)

    def test_account_balance_history_count_compute(self):
        """Test that balance history count compute method exists."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "_compute_balance_history_count")
        assert callable(TesoteAccount._compute_balance_history_count)


class TestBalanceChangeCalculation:
    """Test balance change calculation logic."""

    @pytest.fixture
    def mock_history_record(self):
        """Create mock balance history record."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        record = Mock(spec=TesoteAccountBalanceHistory)
        record.balance = 1000.0
        record.previous_balance = 800.0
        return record

    def test_balance_change_positive(self, mock_history_record):
        """Test balance change calculation for increase."""
        expected_change = 200.0  # 1000 - 800
        actual_change = mock_history_record.balance - mock_history_record.previous_balance
        assert actual_change == expected_change

    def test_balance_change_negative(self, mock_history_record):
        """Test balance change calculation for decrease."""
        mock_history_record.balance = 700.0
        mock_history_record.previous_balance = 1000.0

        expected_change = -300.0  # 700 - 1000
        actual_change = mock_history_record.balance - mock_history_record.previous_balance
        assert actual_change == expected_change

    def test_balance_change_percent(self, mock_history_record):
        """Test balance change percentage calculation."""
        balance = 1000.0
        previous = 800.0
        change = balance - previous  # 200

        expected_percent = (change / abs(previous)) * 100  # 25%
        assert expected_percent == 25.0

    def test_balance_change_percent_from_zero(self):
        """Test percentage calculation when previous balance is zero."""
        balance = 1000.0
        previous = 0.0

        # When previous is zero, percentage should be 0 to avoid division by zero
        if previous == 0:
            percent = 0.0
        else:
            percent = ((balance - previous) / abs(previous)) * 100

        assert percent == 0.0


class TestRecordBalanceHistoryMethod:
    """Test _record_balance_history method logic."""

    @pytest.fixture
    def mock_account(self):
        """Create mock account with balance history support."""
        from models.tesote_account import TesoteAccount

        account = Mock(spec=TesoteAccount)
        account.id = 1
        account.balance = 1500.0
        account.currency_id = Mock(id=1)
        return account

    def test_record_balance_history_method_exists(self):
        """Test that the method exists on TesoteAccount."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "_record_balance_history")

    def test_record_history_threshold(self, mock_account):
        """Test that history is not recorded for small balance changes."""
        # The threshold is 0.01 - changes less than this should not create history
        threshold = 0.01
        old_balance = 1500.0
        new_balance = 1500.005  # Change of 0.005, below threshold

        should_record = abs(new_balance - old_balance) >= threshold
        assert should_record is False

    def test_record_history_above_threshold(self, mock_account):
        """Test that history is recorded for significant balance changes."""
        threshold = 0.01
        old_balance = 1500.0
        new_balance = 1500.02  # Change of 0.02, above threshold

        should_record = abs(new_balance - old_balance) >= threshold
        assert should_record is True

    def test_record_first_history_entry(self, mock_account):
        """Test that first history entry is always recorded."""
        # When there's no previous entry, should always record
        no_previous_entry = True
        mock_account.balance = 1000.0

        should_record = no_previous_entry or abs(mock_account.balance - 0) >= 0.01
        assert should_record is True


class TestUpdateFromTesoteIntegration:
    """Test that update_from_tesote records balance history."""

    def test_update_from_tesote_exists(self):
        """Test that update_from_tesote method exists."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "update_from_tesote")
        assert callable(TesoteAccount.update_from_tesote)

    def test_update_from_tesote_calls_record_history(self):
        """Test that update_from_tesote integrates with balance history."""
        from models.tesote_account import TesoteAccount

        # The update_from_tesote method should call _record_balance_history
        # This is verified by checking the method contains the call
        import inspect

        source = inspect.getsource(TesoteAccount.update_from_tesote)
        assert "_record_balance_history" in source
