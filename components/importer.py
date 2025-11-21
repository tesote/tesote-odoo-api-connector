# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Importer.
Import accounts and transactions from Tesote API.
"""

from typing import Any

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="sync")


class TesoteImporter:
    """Base importer for Tesote."""

    def __init__(self, env, backend_id: int):
        """
        Initialize importer.

        Args:
            env: Odoo environment
            backend_id: Backend record ID
        """
        self.env = env
        self.backend_id = backend_id


class TesoteAccountBatchImporter(TesoteImporter):
    """Import accounts in batch."""

    def run(self, adapter) -> int:
        """
        Import all accounts from Tesote.

        Args:
            adapter: TesoteAdapter instance

        Returns:
            Number of accounts imported
        """
        # Fetch accounts with pagination
        page = 1
        total_imported = 0

        while True:
            result = adapter.list_accounts(page=page, per_page=100)
            accounts = result.get("accounts", [])

            if not accounts:
                break

            for account_data in accounts:
                self._import_account(account_data)
                total_imported += 1

            # Check if more pages
            pagination = result.get("pagination", {})
            if page >= pagination.get("total_pages", 1):
                break
            page += 1

        _logger.info(f"Imported {total_imported} accounts")
        return total_imported

    def _import_account(self, account_data: dict[str, Any]) -> None:
        """Import single account."""
        TesoteAccount = self.env["tesote.account"]

        # Check if account exists
        existing = TesoteAccount.search(
            [
                ("tesote_id", "=", account_data["id"]),
                ("backend_id", "=", self.backend_id),
            ]
        )

        if existing:
            existing.update_from_tesote(account_data)
            _logger.info(f"Updated account {account_data['id']}")
        else:
            backend = self.env["tesote.backend"].browse(self.backend_id)
            TesoteAccount.create_from_tesote(backend, account_data)
            _logger.info(f"Created account {account_data['id']}")


class TesoteAccountImporter(TesoteImporter):
    """Import single account."""

    def run(self, external_id: str, adapter) -> None:
        """
        Import account by Tesote ID.

        Args:
            external_id: Tesote account ID
            adapter: TesoteAdapter instance
        """
        # Fetch account data
        account_data = adapter.get_account(external_id)

        if account_data:
            self._import_account(account_data)

    def _import_account(self, account_data: dict[str, Any]) -> None:
        """Import account data."""
        TesoteAccount = self.env["tesote.account"]

        # Check if account exists
        existing = TesoteAccount.search(
            [
                ("tesote_id", "=", account_data["id"]),
                ("backend_id", "=", self.backend_id),
            ]
        )

        if existing:
            existing.update_from_tesote(account_data)
            _logger.info(f"Updated account {account_data['id']}")
        else:
            backend = self.env["tesote.backend"].browse(self.backend_id)
            TesoteAccount.create_from_tesote(backend, account_data)
            _logger.info(f"Created account {account_data['id']}")


class TesoteTransactionSyncImporter(TesoteImporter):
    """
    Import transactions using v2 sync endpoint.
    Handles added, modified, and removed transactions.
    """

    def run(self, account, adapter) -> int:
        """
        Sync transactions for an account.

        Args:
            account: tesote.account record
            adapter: TesoteAdapter instance

        Returns:
            Number of transactions synced
        """
        # Get stored cursor
        cursor = account.sync_cursor or "latest"
        has_more = True
        total_synced = 0

        while has_more:
            # Call sync endpoint
            sync_result = adapter.sync_transactions(
                tesote_account_id=account.tesote_id,
                cursor=cursor,
                count=500,  # Max allowed
            )

            # Process results
            self._process_sync_results(account, sync_result)

            # Update counts
            total_synced += len(sync_result.get("added", []))
            total_synced += len(sync_result.get("modified", []))
            total_synced += len(sync_result.get("removed", []))

            # Update cursor and check for more
            cursor = sync_result.get("next_cursor")
            has_more = sync_result.get("has_more", False)

            if cursor:
                account.sync_cursor = cursor

        _logger.info(f"Synced {total_synced} transactions for account {account.name}")
        return total_synced

    def _process_sync_results(self, account, sync_result: dict[str, Any]) -> None:
        """Process sync results."""
        TesoteTransaction = self.env["tesote.transaction"]
        try:
            # Try Odoo module import
            from odoo.addons.tesote_connector.components.mapper import TesoteTransactionImportMapper
        except ImportError:
            try:
                # Try relative import
                from .mapper import TesoteTransactionImportMapper
            except ImportError:
                # Fall back to absolute import for tests
                from components.mapper import TesoteTransactionImportMapper

        mapper = TesoteTransactionImportMapper(self.env, self.backend_id)

        # Process removed transactions
        for removed in sync_result.get("removed", []):
            transaction = TesoteTransaction.search(
                [("tesote_id", "=", removed["transaction_id"]), ("account_id", "=", account.id)]
            )
            if transaction:
                transaction.unlink()
                _logger.info(f"Removed transaction {removed['transaction_id']}")

        # Process modified transactions
        for modified in sync_result.get("modified", []):
            transaction = TesoteTransaction.search(
                [("tesote_id", "=", modified["transaction_id"]), ("account_id", "=", account.id)]
            )
            if transaction:
                mapped_data = mapper.map_record(modified, account_id=account.id)
                transaction.write(mapped_data)
                _logger.info(f"Updated transaction {modified['transaction_id']}")

        # Process added transactions
        for added in sync_result.get("added", []):
            # Check if already exists
            existing = TesoteTransaction.search(
                [("tesote_id", "=", added["transaction_id"]), ("account_id", "=", account.id)]
            )
            if not existing:
                mapped_data = mapper.map_record(added, account_id=account.id)
                TesoteTransaction.create(mapped_data)
                _logger.info(f"Added transaction {added['transaction_id']}")
