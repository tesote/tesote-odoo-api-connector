"""
Tests for Odoo accounting service implementation.

TDD approach: Write tests first, then implement the service.
"""

import unittest
from unittest.mock import MagicMock, patch


class TestOdooAccountingService(unittest.TestCase):
    """Test Odoo-specific accounting service implementation."""

    def setUp(self):
        """Set up mocked Odoo environment."""
        self.env = MagicMock()
        self.Account = MagicMock()
        self.env.__getitem__.return_value.sudo.return_value = self.Account

    def test_initialization(self):
        """Test service initialization with Odoo env."""
        from services.odoo_accounting_service import OdooAccountingService

        service = OdooAccountingService(self.env)

        self.assertIsNotNone(service)
        self.assertEqual(service.env, self.env)
        self.env.__getitem__.assert_called_with("account.account")

    def test_get_accounts_first_page_no_cursor(self):
        """Test getting first page of accounts without cursor."""
        from services.odoo_accounting_service import OdooAccountingService

        # Mock accounts with IDs 1-10
        mock_accounts = []
        for i in range(1, 11):
            mock_acc = MagicMock()
            mock_acc.id = i
            mock_acc.code = f"10{i}0"
            mock_acc.name = f"Account {i}"
            mock_accounts.append(mock_acc)

        self.Account.search.return_value = mock_accounts

        service = OdooAccountingService(self.env)

        with patch("services.odoo_accounting_service.AccountSchema") as MockSchema:
            MockSchema.from_odoo.side_effect = lambda acc: {
                "id": str(acc.id),
                "code": acc.code,
                "name": acc.name,
            }

            accounts, next_cursor, has_more = service.get_accounts(cursor=None, limit=10)

        # Verify results
        self.assertEqual(len(accounts), 10)
        self.assertEqual(next_cursor, "10")  # Last ID in batch
        self.assertTrue(has_more)  # Exactly limit records = more may exist

        # Verify search was called correctly
        search_call = self.Account.search.call_args
        self.assertEqual(search_call.kwargs["limit"], 10)
        self.assertEqual(search_call.kwargs["order"], "id ASC")

    def test_get_accounts_with_cursor(self):
        """Test cursor-based pagination."""
        from services.odoo_accounting_service import OdooAccountingService

        # Mock accounts with IDs 11-20
        mock_accounts = []
        for i in range(11, 21):
            mock_acc = MagicMock()
            mock_acc.id = i
            mock_accounts.append(mock_acc)

        self.Account.search.return_value = mock_accounts

        service = OdooAccountingService(self.env)

        with patch("services.odoo_accounting_service.AccountSchema") as MockSchema:
            MockSchema.from_odoo.side_effect = lambda acc: {"id": str(acc.id)}

            accounts, next_cursor, has_more = service.get_accounts(cursor="10", limit=10)

        # Verify cursor was used in domain
        search_call = self.Account.search.call_args
        domain = search_call.args[0]
        self.assertIn(("id", ">", 10), domain)

        # Verify pagination metadata
        self.assertEqual(len(accounts), 10)
        self.assertEqual(next_cursor, "20")
        self.assertTrue(has_more)

    def test_get_accounts_last_page(self):
        """Test last page with partial results."""
        from services.odoo_accounting_service import OdooAccountingService

        # Mock only 5 accounts (less than limit)
        mock_accounts = [MagicMock(id=i) for i in range(21, 26)]
        self.Account.search.return_value = mock_accounts

        service = OdooAccountingService(self.env)

        with patch("services.odoo_accounting_service.AccountSchema") as MockSchema:
            MockSchema.from_odoo.side_effect = lambda acc: {"id": str(acc.id)}

            accounts, next_cursor, has_more = service.get_accounts(cursor="20", limit=10)

        # Verify last page indicators
        self.assertEqual(len(accounts), 5)
        self.assertEqual(next_cursor, "25")
        self.assertFalse(has_more)  # Less than limit = last page

    def test_get_accounts_empty_result(self):
        """Test empty result set."""
        from services.odoo_accounting_service import OdooAccountingService

        self.Account.search.return_value = []

        service = OdooAccountingService(self.env)

        with patch("services.odoo_accounting_service.AccountSchema") as MockSchema:
            accounts, next_cursor, has_more = service.get_accounts(cursor="1000", limit=10)

        # Verify empty result
        self.assertEqual(len(accounts), 0)
        self.assertIsNone(next_cursor)
        self.assertFalse(has_more)

    def test_get_account_by_id_found(self):
        """Test getting account by ID when it exists."""
        from services.odoo_accounting_service import OdooAccountingService

        mock_account = MagicMock()
        mock_account.id = 5
        mock_account.code = "1000"
        mock_account.name = "Cash"
        mock_account.exists.return_value = True

        self.Account.browse.return_value = mock_account

        service = OdooAccountingService(self.env)

        with patch("services.odoo_accounting_service.AccountSchema") as MockSchema:
            MockSchema.from_odoo.return_value = {
                "id": "5",
                "code": "1000",
                "name": "Cash",
            }

            account = service.get_account_by_id("5")

        self.assertIsNotNone(account)
        self.assertEqual(account["id"], "5")
        self.Account.browse.assert_called_with(5)

    def test_get_account_by_id_not_found(self):
        """Test getting account by ID when it doesn't exist."""
        from services.odoo_accounting_service import OdooAccountingService

        mock_account = MagicMock()
        mock_account.exists.return_value = False

        self.Account.browse.return_value = mock_account

        service = OdooAccountingService(self.env)
        account = service.get_account_by_id("999")

        self.assertIsNone(account)

    def test_search_accounts_by_code(self):
        """Test searching accounts by code."""
        from services.odoo_accounting_service import OdooAccountingService

        mock_accounts = [
            MagicMock(id=1, code="1000", name="Cash"),
            MagicMock(id=2, code="1010", name="Bank"),
        ]
        self.Account.search.return_value = mock_accounts

        service = OdooAccountingService(self.env)

        with patch("services.odoo_accounting_service.AccountSchema") as MockSchema:
            MockSchema.from_odoo.side_effect = lambda acc: {
                "id": str(acc.id),
                "code": acc.code,
            }

            accounts, next_cursor, has_more = service.search_accounts(code="10", limit=10)

        # Verify search domain includes code filter
        search_call = self.Account.search.call_args
        domain = search_call.args[0]
        self.assertIn(("code", "ilike", "10"), domain)

        self.assertEqual(len(accounts), 2)

    def test_search_accounts_multiple_filters(self):
        """Test searching with multiple filters."""
        from services.odoo_accounting_service import OdooAccountingService

        self.Account.search.return_value = []

        service = OdooAccountingService(self.env)

        with patch("services.odoo_accounting_service.AccountSchema"):
            service.search_accounts(
                code="10", name="cash", account_type="asset_current", cursor="5", limit=20
            )

        # Verify all filters in domain
        search_call = self.Account.search.call_args
        domain = search_call.args[0]

        self.assertIn(("id", ">", 5), domain)  # Cursor
        self.assertIn(("code", "ilike", "10"), domain)
        self.assertIn(("name", "ilike", "cash"), domain)
        self.assertIn(("account_type", "=", "asset_current"), domain)

    def test_get_account_types(self):
        """Test getting all account types."""
        from services.odoo_accounting_service import OdooAccountingService

        self.Account.read_group.return_value = [
            {"account_type": "asset_current", "account_type_count": 10},
            {"account_type": "liability_payable", "account_type_count": 5},
            {"account_type": None, "account_type_count": 2},  # Should be filtered out
        ]

        service = OdooAccountingService(self.env)
        types = service.get_account_types()

        self.assertEqual(len(types), 2)
        self.assertIn("asset_current", types)
        self.assertIn("liability_payable", types)
        self.assertNotIn(None, types)

    def test_get_statistics(self):
        """Test getting account statistics."""
        from services.odoo_accounting_service import OdooAccountingService

        self.Account.search_count.side_effect = [100, 25, 5]  # total, reconcilable, deprecated

        self.Account.read_group.side_effect = [
            # By type
            [
                {"account_type": "asset_current", "account_type_count": 30},
                {"account_type": "expense", "account_type_count": 20},
            ],
            # By group
            [
                {"internal_group": "asset", "internal_group_count": 40},
                {"internal_group": "expense", "internal_group_count": 20},
            ],
        ]

        service = OdooAccountingService(self.env)
        stats = service.get_statistics()

        self.assertEqual(stats["total_accounts"], 100)
        self.assertEqual(stats["reconcilable_count"], 25)
        self.assertEqual(stats["deprecated_count"], 5)
        self.assertEqual(stats["by_type"]["asset_current"], 30)
        self.assertEqual(stats["by_group"]["asset"], 40)


if __name__ == "__main__":
    unittest.main()
