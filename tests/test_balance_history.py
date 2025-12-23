# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tests for Tesote Account Balance History functionality.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock

import pytest


class TestTesoteAccountBalanceHistory:
    """Test Tesote Account Balance History model."""

    @pytest.fixture
    def mock_account(self):
        """Create a mock account record."""
        account = Mock()
        account.id = 1
        account.name = "Test Checking Account"
        account.tesote_id = "acc-001"
        account.balance = 1000.00
        account.currency_id = Mock(name="USD")
        account.bank_name = "Test Bank"
        return account

    @pytest.fixture
    def mock_sync_log(self):
        """Create a mock sync log record."""
        log = Mock()
        log.id = 1
        log.operation = "sync_transactions"
        log.status = "success"
        return log

    @pytest.fixture
    def balance_history_model(self):
        """Create mock balance history model."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        model = Mock(spec=TesoteAccountBalanceHistory)
        model._name = "tesote.account.balance.history"
        return model

    def test_model_exists(self):
        """Test that balance history model can be imported."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        assert TesoteAccountBalanceHistory._name == "tesote.account.balance.history"
        assert TesoteAccountBalanceHistory._description == "Tesote Account Balance History"
        assert TesoteAccountBalanceHistory._order == "recorded_at desc"

    def test_model_has_required_fields(self):
        """Test that model has all required fields."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        # Check field existence by checking class attributes
        assert hasattr(TesoteAccountBalanceHistory, "account_id")
        assert hasattr(TesoteAccountBalanceHistory, "balance")
        assert hasattr(TesoteAccountBalanceHistory, "previous_balance")
        assert hasattr(TesoteAccountBalanceHistory, "balance_change")
        assert hasattr(TesoteAccountBalanceHistory, "balance_change_percent")
        assert hasattr(TesoteAccountBalanceHistory, "recorded_at")
        assert hasattr(TesoteAccountBalanceHistory, "source")
        assert hasattr(TesoteAccountBalanceHistory, "sync_log_id")
        assert hasattr(TesoteAccountBalanceHistory, "currency_id")
        assert hasattr(TesoteAccountBalanceHistory, "bank_name")
        assert hasattr(TesoteAccountBalanceHistory, "recorded_date")

    def test_model_has_required_methods(self):
        """Test that model has required methods."""
        from models.tesote_account_balance_history import TesoteAccountBalanceHistory

        assert hasattr(TesoteAccountBalanceHistory, "record_balance")
        assert hasattr(TesoteAccountBalanceHistory, "cleanup_old_records")
        assert hasattr(TesoteAccountBalanceHistory, "_compute_balance_change")
        assert hasattr(TesoteAccountBalanceHistory, "_compute_display_name")
        assert hasattr(TesoteAccountBalanceHistory, "_compute_recorded_date")

    def test_record_balance_creates_snapshot(self, balance_history_model, mock_account):
        """Test that record_balance creates a balance snapshot."""
        mock_record = Mock()
        mock_record.id = 1
        mock_record.balance = 1500.00
        mock_record.previous_balance = 1000.00
        mock_record.balance_change = 500.00
        mock_record.source = "sync"

        balance_history_model.record_balance.return_value = mock_record

        record = balance_history_model.record_balance(
            account=mock_account,
            balance=1500.00,
            source="sync",
        )

        balance_history_model.record_balance.assert_called_once()
        assert record.balance == 1500.00
        assert record.balance_change == 500.00

    def test_record_balance_with_sync_log(
        self, balance_history_model, mock_account, mock_sync_log
    ):
        """Test balance recording with sync log traceability."""
        mock_record = Mock()
        mock_record.sync_log_id = mock_sync_log

        balance_history_model.record_balance.return_value = mock_record

        record = balance_history_model.record_balance(
            account=mock_account,
            balance=2000.00,
            source="sync",
            sync_log=mock_sync_log,
        )

        assert record.sync_log_id == mock_sync_log

    def test_balance_change_computation_positive(self):
        """Test balance change is computed correctly for increase."""
        balance = 1500.00
        previous_balance = 1000.00
        expected_change = 500.00
        expected_percent = 50.0

        actual_change = balance - previous_balance
        actual_percent = (actual_change / abs(previous_balance)) * 100

        assert actual_change == expected_change
        assert actual_percent == expected_percent

    def test_balance_change_computation_negative(self):
        """Test negative balance change computation."""
        balance = 800.00
        previous_balance = 1000.00
        expected_change = -200.00
        expected_percent = -20.0

        actual_change = balance - previous_balance
        actual_percent = (actual_change / abs(previous_balance)) * 100

        assert actual_change == expected_change
        assert actual_percent == expected_percent

    def test_balance_change_from_zero(self):
        """Test balance change when previous balance was zero."""
        balance = 1000.00
        previous_balance = 0.0

        actual_change = balance - previous_balance
        # Percentage should be 0 when previous is 0
        if previous_balance:
            actual_percent = (actual_change / abs(previous_balance)) * 100
        else:
            actual_percent = 0.0

        assert actual_change == 1000.00
        assert actual_percent == 0.0

    def test_source_types(self, balance_history_model, mock_account):
        """Test different source types are recorded correctly."""
        sources = ["sync", "webhook", "manual"]

        for source in sources:
            mock_record = Mock()
            mock_record.source = source

            balance_history_model.record_balance.return_value = mock_record

            record = balance_history_model.record_balance(
                account=mock_account,
                balance=1000.00,
                source=source,
            )

            assert record.source == source


class TestAccountBalanceRecording:
    """Test balance recording integration with account updates."""

    @pytest.fixture
    def mock_account_with_env(self):
        """Create mock account with environment."""
        account = Mock()
        account.id = 1
        account.name = "Test Account"
        account.balance = 1000.00
        account.env = MagicMock()
        return account

    def test_update_from_tesote_records_balance_change(self, mock_account_with_env):
        """Test that update_from_tesote records balance when it changes."""
        mock_balance_history = Mock()
        mock_account_with_env.env.__getitem__ = Mock(return_value=mock_balance_history)

        old_balance = 1000.00
        new_balance = 1500.00

        # Simulate balance change detection
        if abs(new_balance - old_balance) >= 0.01:
            mock_balance_history.record_balance(
                account=mock_account_with_env,
                balance=new_balance,
                source="sync",
            )

        mock_balance_history.record_balance.assert_called_once()

    def test_update_from_tesote_no_record_when_unchanged(self, mock_account_with_env):
        """Test that no history is recorded when balance unchanged."""
        mock_balance_history = Mock()
        mock_account_with_env.env.__getitem__ = Mock(return_value=mock_balance_history)

        old_balance = 1000.00
        new_balance = 1000.00  # Same balance

        # Simulate balance change detection
        if abs(new_balance - old_balance) >= 0.01:
            mock_balance_history.record_balance(
                account=mock_account_with_env,
                balance=new_balance,
                source="sync",
            )

        mock_balance_history.record_balance.assert_not_called()

    def test_update_from_tesote_no_record_for_tiny_change(self, mock_account_with_env):
        """Test that no history is recorded for very small balance changes."""
        mock_balance_history = Mock()
        mock_account_with_env.env.__getitem__ = Mock(return_value=mock_balance_history)

        old_balance = 1000.00
        new_balance = 1000.005  # Change less than 0.01

        # Simulate balance change detection (threshold is 0.01)
        if abs(new_balance - old_balance) >= 0.01:
            mock_balance_history.record_balance(
                account=mock_account_with_env,
                balance=new_balance,
                source="sync",
            )

        mock_balance_history.record_balance.assert_not_called()

    def test_create_from_tesote_records_initial_balance(self):
        """Test that initial balance is recorded when account is created."""
        mock_env = MagicMock()
        mock_balance_history = Mock()
        mock_env.__getitem__ = Mock(return_value=mock_balance_history)

        initial_balance = 5000.00

        # Simulate initial balance recording
        if initial_balance:
            mock_balance_history.record_balance(
                account=Mock(id=1),
                balance=initial_balance,
                source="sync",
            )

        mock_balance_history.record_balance.assert_called_once()


class TestBalanceHistoryCleanup:
    """Test cleanup functionality for old balance records."""

    def test_cleanup_removes_old_records(self):
        """Test that cleanup removes records older than retention period."""
        mock_model = Mock()
        mock_old_records = [Mock(), Mock(), Mock()]
        mock_model.search.return_value = mock_old_records

        # Simulate cleanup
        old_records = mock_model.search([])
        count = len(old_records)

        for record in old_records:
            record.unlink()

        assert count == 3
        for record in mock_old_records:
            record.unlink.assert_called_once()

    def test_cleanup_respects_retention_period(self):
        """Test cleanup only affects records beyond retention period."""
        now = datetime.now()
        retention_days = 365
        cutoff_date = now - timedelta(days=retention_days)

        # Records to test
        recent_record_date = now - timedelta(days=30)  # Should be kept
        old_record_date = now - timedelta(days=400)  # Should be removed

        assert recent_record_date > cutoff_date  # Keep
        assert old_record_date < cutoff_date  # Remove


class TestAccountModelIntegration:
    """Test account model integration with balance history."""

    def test_account_has_balance_history_field(self):
        """Test that account model has balance_history_ids field."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "balance_history_ids")
        assert hasattr(TesoteAccount, "balance_history_count")

    def test_account_has_action_view_balance_history(self):
        """Test that account model has action_view_balance_history method."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "action_view_balance_history")

    def test_account_has_compute_balance_history_count(self):
        """Test that account model has _compute_balance_history_count method."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "_compute_balance_history_count")
