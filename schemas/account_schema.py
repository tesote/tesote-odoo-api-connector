"""
Generic account schema (DTO) for API responses.

This schema is ERP-agnostic - works with Odoo, SAP, NetSuite, etc.
Maps ERP-specific account structures to a standardized format.
"""

from typing import Any


class AccountSchema:
    """
    Generic account data transfer object.

    This is a dict-based schema (not an Odoo model) for maximum portability.
    """

    @staticmethod
    def from_odoo(account) -> dict[str, Any]:
        """
        Convert Odoo account.account to generic schema.

        Args:
            account: Odoo account.account record

        Returns:
            Generic account dict

        Example:
            >>> from schemas.account_schema import AccountSchema
            >>> odoo_account = env['account.account'].browse(1)
            >>> generic_account = AccountSchema.from_odoo(odoo_account)
            >>> print(generic_account['code'])
            '1000'
        """
        return {
            # Core identification
            "id": str(account.id),
            "code": account.code or "",
            "name": account.name or "",
            # Classification
            "account_type": account.account_type or "",
            "internal_group": account.internal_group or "",
            # Properties
            "reconcile": bool(account.reconcile),
            "deprecated": bool(account.deprecated),
            # Currency
            "currency_id": account.currency_id.id if account.currency_id else None,
            "currency_code": account.currency_id.name if account.currency_id else None,
            # Company (Odoo 18: company_ids is Many2many, get first company)
            "company_id": account.company_ids[0].id if account.company_ids else None,
            "company_name": account.company_ids[0].name if account.company_ids else "",
            # Balance
            "current_balance": (
                float(account.current_balance) if hasattr(account, "current_balance") else 0.0
            ),
            # Relationships
            "allowed_journal_ids": (
                [j.id for j in account.allowed_journal_ids]
                if hasattr(account, "allowed_journal_ids")
                else []
            ),
            # Tags
            "tag_ids": [
                {"id": t.id, "name": t.name}
                for t in (account.tag_ids if hasattr(account, "tag_ids") else [])
            ],
            # Notes
            "note": account.note or "",
        }

    @staticmethod
    def from_sap(gl_account: dict) -> dict[str, Any]:
        """
        Convert SAP GL account to generic schema.

        This is a placeholder for future SAP integration.

        Args:
            gl_account: SAP GL account data (dict)

        Returns:
            Generic account dict

        Example (future):
            >>> sap_account = {"GLAccount": "1000", "GLAccountName": "Cash", ...}
            >>> generic_account = AccountSchema.from_sap(sap_account)
        """
        # Placeholder implementation for SAP
        # SAP field names will differ from Odoo
        return {
            "id": gl_account.get("GLAccount", ""),
            "code": gl_account.get("GLAccount", ""),
            "name": gl_account.get("GLAccountName", ""),
            "account_type": gl_account.get("AccountType", ""),
            "internal_group": gl_account.get("AccountGroup", ""),
            "reconcile": gl_account.get("Reconcilable", False),
            "deprecated": gl_account.get("Blocked", False),
            "currency_id": None,
            "currency_code": gl_account.get("Currency", ""),
            "company_id": None,
            "company_name": gl_account.get("CompanyCode", ""),
            "current_balance": 0.0,
            "allowed_journal_ids": [],
            "tag_ids": [],
            "note": "",
        }

    @staticmethod
    def to_dict(
        id: str, code: str, name: str, account_type: str = "", internal_group: str = "", **kwargs
    ) -> dict[str, Any]:
        """
        Create generic account dict from raw data.

        This is useful for testing or manual construction.

        Args:
            id: Account ID
            code: Account code
            name: Account name
            account_type: Account type
            internal_group: Internal grouping
            **kwargs: Additional fields

        Returns:
            Generic account dict
        """
        account = {
            "id": str(id),
            "code": code,
            "name": name,
            "account_type": account_type,
            "internal_group": internal_group,
            "reconcile": kwargs.get("reconcile", False),
            "deprecated": kwargs.get("deprecated", False),
            "currency_id": kwargs.get("currency_id"),
            "currency_code": kwargs.get("currency_code"),
            "company_id": kwargs.get("company_id"),
            "company_name": kwargs.get("company_name", ""),
            "current_balance": kwargs.get("current_balance", 0.0),
            "allowed_journal_ids": kwargs.get("allowed_journal_ids", []),
            "tag_ids": kwargs.get("tag_ids", []),
            "note": kwargs.get("note", ""),
        }
        return account

    @staticmethod
    def validate(account: dict[str, Any]) -> bool:
        """
        Validate generic account schema.

        Args:
            account: Account dict to validate

        Returns:
            True if valid, raises ValueError if invalid

        Raises:
            ValueError: If validation fails
        """
        required_fields = ["id", "code", "name"]

        for field in required_fields:
            if field not in account:
                raise ValueError(f"Missing required field: {field}")
            if not account[field]:
                raise ValueError(f"Field '{field}' cannot be empty")

        return True
