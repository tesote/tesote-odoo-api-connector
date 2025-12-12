"""
Abstract base accounting service (ERP-agnostic).

This interface defines the contract for accounting services across any ERP.
Implementations: OdooAccountingService, SapAccountingService, etc.

IMPORTANT: This file has ZERO Odoo dependencies.
Only Python stdlib + typing.
"""

from abc import ABC, abstractmethod


class BaseAccountingService(ABC):
    """
    Abstract base for accounting services across ERPs.

    This interface is ERP-agnostic. Concrete implementations handle
    ERP-specific logic (Odoo, SAP, NetSuite, etc.).

    All methods return generic dicts (not ERP-specific objects) for
    maximum portability and API consistency.
    """

    @abstractmethod
    def get_accounts(
        self, cursor: str | None = None, limit: int = 100, filters: dict | None = None
    ) -> tuple[list[dict], str | None, bool]:
        """
        Get accounts with cursor-based pagination.

        Cursor pagination is fast (O(1)) and stateless.
        Uses ID as cursor: WHERE id > cursor ORDER BY id ASC

        Args:
            cursor: Last seen ID (for pagination). None for first page.
            limit: Max records to return (1-500)
            filters: Optional filters dict:
                - type: Account type (exact match)
                - group: Internal group (exact match)

        Returns:
            Tuple of (accounts_list, next_cursor, has_more):
                - accounts_list: List of account dicts (generic schema)
                - next_cursor: Cursor for next page (or None if last page)
                - has_more: Boolean - are there more records?

        Example:
            >>> service = OdooAccountingService(env)
            >>> accounts, next_cursor, has_more = service.get_accounts(
            ...     cursor=None,  # First page
            ...     limit=100
            ... )
            >>> print(len(accounts))  # 100
            >>> print(next_cursor)  # "100" (last ID in batch)
            >>> print(has_more)  # True (more records exist)
        """
        pass

    @abstractmethod
    def get_account_by_id(self, account_id: str) -> dict | None:
        """
        Get single account by ID.

        Args:
            account_id: Account ID (string for flexibility across ERPs)

        Returns:
            Account dict (generic schema) or None if not found

        Example:
            >>> service = OdooAccountingService(env)
            >>> account = service.get_account_by_id("123")
            >>> print(account['code'])  # "1000"
            >>> print(account['name'])  # "Cash"
        """
        pass

    @abstractmethod
    def search_accounts(
        self,
        code: str | None = None,
        name: str | None = None,
        account_type: str | None = None,
        internal_group: str | None = None,
        cursor: str | None = None,
        limit: int = 100,
    ) -> tuple[list[dict], str | None, bool]:
        """
        Search accounts by fields.

        Text fields (code, name) use partial match (ILIKE/LIKE).
        Enum fields (type, group) use exact match.

        Args:
            code: Account code (partial match, case-insensitive)
            name: Account name (partial match, case-insensitive)
            account_type: Account type (exact match)
            internal_group: Internal group (exact match)
            cursor: Pagination cursor
            limit: Max records

        Returns:
            Tuple of (accounts_list, next_cursor, has_more)

        Example:
            >>> service = OdooAccountingService(env)
            >>> accounts, cursor, has_more = service.search_accounts(
            ...     code="10",  # Matches "1000", "1010", etc.
            ...     account_type="asset_current"
            ... )
        """
        pass

    @abstractmethod
    def get_account_types(self) -> list[str]:
        """
        Get list of all account types.

        Returns:
            List of account type codes (strings)

        Example:
            >>> service = OdooAccountingService(env)
            >>> types = service.get_account_types()
            >>> print(types)
            ['asset_current', 'asset_non_current', 'liability_payable', ...]
        """
        pass

    @abstractmethod
    def get_statistics(self) -> dict:
        """
        Get accounting statistics.

        Returns:
            Dict with statistics:
                - total_accounts: Total number of accounts (int)
                - by_type: Accounts grouped by type (Dict[str, int])
                - by_group: Accounts grouped by internal group (Dict[str, int])
                - reconcilable_count: Number of reconcilable accounts (int)

        Example:
            >>> service = OdooAccountingService(env)
            >>> stats = service.get_statistics()
            >>> print(stats['total_accounts'])  # 51
            >>> print(stats['by_type']['asset_current'])  # 15
            >>> print(stats['reconcilable_count'])  # 8
        """
        pass
