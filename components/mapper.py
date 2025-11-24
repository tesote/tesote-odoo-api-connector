# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Data Mapper.
Transforms data between Tesote and Odoo formats.
"""

from typing import Any

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="sync")


class TesoteMapper:
    """
    Base mapper for transforming data between Tesote and Odoo.
    """

    def __init__(self, env, backend_id: int):
        """
        Initialize mapper.

        Args:
            env: Odoo environment
            backend_id: Backend record ID
        """
        self.env = env
        self.backend_id = backend_id

    def _map_direct(self, record: dict[str, Any], mappings: dict[str, str]) -> dict[str, Any]:
        """
        Apply direct field mappings.

        Args:
            record: Source record
            mappings: Field mappings {odoo_field: tesote_field}

        Returns:
            Mapped values
        """
        result = {}
        for odoo_field, tesote_field in mappings.items():
            if tesote_field in record:
                result[odoo_field] = record[tesote_field]
        return result

    def finalize(self, map_record: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
        """
        Finalize mapped values.

        Args:
            map_record: Original Tesote record
            values: Mapped values

        Returns:
            Finalized values
        """
        # Add backend_id to all records
        values["backend_id"] = self.backend_id
        return values


class TesoteAccountImportMapper(TesoteMapper):
    """
    Map Tesote account data to Odoo format.
    """

    # Direct field mappings
    direct = [
        ("id", "tesote_id"),
        ("name", "name"),
    ]

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """
        Map Tesote account to Odoo account.

        Args:
            record: Tesote account data

        Returns:
            Odoo account values
        """
        values = {}

        # Direct mappings
        values["tesote_id"] = record.get("id")
        values["name"] = record.get("name")

        # Map bank information
        values["bank_name"] = record.get("bank", {}).get("name")
        values["legal_entity_name"] = record.get("legal_entity", {}).get("name")

        # Map timestamps
        values["tesote_created_at"] = record.get("tesote_created_at")
        values["tesote_updated_at"] = record.get("tesote_updated_at")

        return self.finalize(record, values)


class TesoteTransactionImportMapper(TesoteMapper):
    """
    Map Tesote transaction sync data to Odoo format.
    """

    # Direct field mappings
    direct = [
        ("transaction_id", "tesote_id"),
        ("name", "name"),
        ("amount", "amount"),
        ("date", "transaction_date"),
        ("merchant_name", "counterparty_name"),
    ]

    def map_record(self, record: dict[str, Any], account_id: int | None = None) -> dict[str, Any]:
        """
        Map Tesote transaction to Odoo transaction.

        Args:
            record: Tesote transaction data
            account_id: Optional account ID to link to

        Returns:
            Odoo transaction values
        """
        values = {}

        # Direct mappings
        values["tesote_id"] = record.get("transaction_id")
        values["name"] = record.get("name")
        values["amount"] = record.get("amount")
        values["transaction_date"] = record.get("date")
        values["counterparty_name"] = record.get("merchant_name")

        # Map account if provided
        if account_id:
            values["account_id"] = account_id

        # Map status based on pending flag
        values["status"] = "pending" if record.get("pending", False) else "completed"

        # Map categories
        categories = record.get("category", [])
        values["categories"] = ", ".join(categories) if categories else ""

        # Map currency
        currency_code = record.get("iso_currency_code", "USD")
        currency = self.env["res.currency"].search([("name", "=", currency_code)], limit=1)

        if not currency:
            currency = self.env.company.currency_id

        values["currency_id"] = currency.id

        # Map timestamps
        values["tesote_imported_at"] = record.get("datetime")
        values["tesote_updated_at"] = record.get("datetime")

        return self.finalize(record, values)
