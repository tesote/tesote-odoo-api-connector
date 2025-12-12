"""
Odoo accounting service implementation.

This service implements the BaseAccountingService interface for Odoo ERP.
Uses Odoo's account.account model and maps to generic schema.
"""

try:
    from ..schemas.account_schema import AccountSchema
    from .base_accounting_service import BaseAccountingService
except ImportError:
    from schemas.account_schema import AccountSchema
    from services.base_accounting_service import BaseAccountingService


class OdooAccountingService(BaseAccountingService):
    """
    Odoo implementation of accounting service.

    This is the ONLY service file that imports Odoo.
    All other service files are ERP-agnostic.
    """

    def __init__(self, env):
        """
        Initialize with Odoo environment.

        Args:
            env: Odoo environment (request.env)
        """
        self.env = env
        self.Account = env["account.account"].sudo()

    def get_accounts(
        self, cursor: str | None = None, limit: int = 100, filters: dict | None = None
    ) -> tuple[list[dict], str | None, bool]:
        """
        Get accounts with cursor-based pagination.

        Cursor pagination: WHERE id > cursor ORDER BY id ASC
        Much faster than OFFSET for large datasets (O(1) vs O(n)).

        Args:
            cursor: Last seen ID (for pagination). None for first page.
            limit: Max records to return (1-500)
            filters: Optional filters dict (type, group)

        Returns:
            Tuple of (accounts_list, next_cursor, has_more)
        """
        # Build domain
        domain = []

        # Cursor pagination filter (CRITICAL: must be first)
        if cursor:
            try:
                cursor_id = int(cursor)
                domain.append(("id", ">", cursor_id))
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid cursor: {cursor}") from e

        # Additional filters
        if filters:
            if "type" in filters:
                domain.append(("account_type", "=", filters["type"]))
            if "group" in filters:
                domain.append(("internal_group", "=", filters["group"]))

        # Execute query with cursor
        # CRITICAL: Must order by id ASC for cursor pagination to work
        accounts = self.Account.search(domain, limit=limit, order="id ASC")

        # Map to generic schema
        accounts_list = [AccountSchema.from_odoo(acc) for acc in accounts]

        # Calculate pagination metadata
        next_cursor = str(accounts[-1].id) if accounts else None
        has_more = len(accounts) == limit  # If exactly limit, more may exist

        return accounts_list, next_cursor, has_more

    def get_account_by_id(self, account_id: str) -> dict | None:
        """
        Get single account by ID.

        Args:
            account_id: Account ID (string)

        Returns:
            Account dict (generic schema) or None if not found
        """
        try:
            account = self.Account.browse(int(account_id))

            if not account.exists():
                return None

            return AccountSchema.from_odoo(account)

        except (ValueError, TypeError):
            return None

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

        Text fields use partial match (ILIKE).
        Enum fields use exact match.

        Args:
            code: Account code (partial match, case-insensitive)
            name: Account name (partial match, case-insensitive)
            account_type: Account type (exact match)
            internal_group: Internal group (exact match)
            cursor: Pagination cursor (last seen ID)
            limit: Max records

        Returns:
            Tuple of (accounts_list, next_cursor, has_more)
        """
        domain = []

        # Cursor pagination (CRITICAL: must be first)
        if cursor:
            try:
                cursor_id = int(cursor)
                domain.append(("id", ">", cursor_id))
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid cursor: {cursor}") from e

        # Search filters
        if code:
            domain.append(("code", "ilike", code))
        if name:
            domain.append(("name", "ilike", name))
        if account_type:
            domain.append(("account_type", "=", account_type))
        if internal_group:
            domain.append(("internal_group", "=", internal_group))

        # Execute search with cursor
        accounts = self.Account.search(domain, limit=limit, order="id ASC")

        # Map to generic schema
        accounts_list = [AccountSchema.from_odoo(acc) for acc in accounts]

        # Pagination metadata
        next_cursor = str(accounts[-1].id) if accounts else None
        has_more = len(accounts) == limit

        return accounts_list, next_cursor, has_more

    def get_account_types(self) -> list[str]:
        """
        Get list of all account types.

        Uses read_group for efficiency (no record loading).

        Returns:
            List of account type codes
        """
        result = self.Account.read_group(
            domain=[], fields=["account_type"], groupby=["account_type"]
        )

        # Filter out None/empty types
        return [r["account_type"] for r in result if r.get("account_type")]

    def get_statistics(self) -> dict:
        """
        Get accounting statistics.

        Uses read_group and search_count for efficiency (no record loading).

        Returns:
            Dict with statistics
        """
        # Total accounts
        total_accounts = self.Account.search_count([])

        # Group by account type
        type_groups = self.Account.read_group(
            domain=[], fields=["account_type"], groupby=["account_type"]
        )
        by_type = {g["account_type"] or "unspecified": g["account_type_count"] for g in type_groups}

        # Group by internal group
        group_groups = self.Account.read_group(
            domain=[], fields=["internal_group"], groupby=["internal_group"]
        )
        by_group = {
            g["internal_group"] or "unspecified": g["internal_group_count"] for g in group_groups
        }

        # Specific attribute counts
        reconcilable_count = self.Account.search_count([("reconcile", "=", True)])
        deprecated_count = self.Account.search_count([("deprecated", "=", True)])

        return {
            "total_accounts": total_accounts,
            "by_type": by_type,
            "by_group": by_group,
            "reconcilable_count": reconcilable_count,
            "deprecated_count": deprecated_count,
        }
