"""
API Controller for exposing Odoo accounting accounts as REST endpoints.

This module provides RESTful API endpoints for accessing accounting accounts data.
"""

from datetime import datetime

from odoo import http
from odoo.http import request

try:
    from ..schemas.account_schema import AccountSchema
    from ..utils.colored_logger import get_logger
except ImportError:
    from schemas.account_schema import AccountSchema
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="api")


class AccountingAPIController(http.Controller):
    """RESTful API controller for accessing accounting accounts."""

    def _get_account_data(self, account):
        """
        Convert account record to dictionary using AccountSchema.

        Args:
            account: account.account record

        Returns:
            dict: Account data (ERP-agnostic format)
        """
        return AccountSchema.from_odoo(account)

    @http.route("/api/v1/accounts", type="json", auth="user", methods=["GET"], csrf=False)
    def get_accounts(self, limit=100, offset=0, domain=None, **kwargs):
        """
        Get list of accounting accounts.

        Query parameters:
            limit (int): Maximum number of records to return (default: 100, max: 500)
            offset (int): Number of records to skip (default: 0)
            domain (list): Odoo domain filter (optional)

        Returns:
            dict: Response with accounts list and metadata
        """
        try:
            # Validate input parameters
            try:
                limit = max(1, min(int(limit), 500))  # Clamp between 1-500
                offset = max(0, int(offset))
            except (ValueError, TypeError):
                return {
                    "status": "error",
                    "error": "Invalid pagination parameters",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            _logger.info(f"API request: GET /api/v1/accounts (limit={limit}, offset={offset})")

            # Parse domain
            search_domain = domain if domain else []

            # Get accounts
            # NOTE: Using sudo() to grant API access regardless of user permissions.
            # This is intentional for API endpoints. Future: Implement API key-based access control.
            Account = request.env["account.account"].sudo()
            total_count = Account.search_count(search_domain)
            accounts = Account.search(search_domain, limit=limit, offset=offset, order="code ASC")

            # Convert to list of dicts
            accounts_data = [self._get_account_data(acc) for acc in accounts]

            response = {
                "status": "success",
                "data": accounts_data,
                "metadata": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "count": len(accounts_data),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            _logger.info(f"API response: {len(accounts_data)} accounts returned")
            return response

        except Exception as e:
            _logger.error(f"Error in get_accounts: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e), "timestamp": datetime.utcnow().isoformat()}

    @http.route(
        "/api/v1/accounts/<int:account_id>", type="json", auth="user", methods=["GET"], csrf=False
    )
    def get_account(self, account_id, **kwargs):
        """
        Get single accounting account by ID.

        Args:
            account_id (int): Account ID

        Returns:
            dict: Response with account data
        """
        try:
            _logger.info(f"API request: GET /api/v1/accounts/{account_id}")

            Account = request.env["account.account"].sudo()
            account = Account.browse(account_id)

            if not account.exists():
                return {
                    "status": "error",
                    "error": "Account not found",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            response = {
                "status": "success",
                "data": self._get_account_data(account),
                "timestamp": datetime.utcnow().isoformat(),
            }

            _logger.info(f"API response: Account {account_id} retrieved")
            return response

        except Exception as e:
            _logger.error(f"Error in get_account: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e), "timestamp": datetime.utcnow().isoformat()}

    @http.route("/api/v1/accounts/search", type="json", auth="user", methods=["POST"], csrf=False)
    def search_accounts(
        self, code=None, name=None, account_type=None, limit=100, offset=0, **kwargs
    ):
        """
        Search accounting accounts with filters.

        Body parameters:
            code (str): Filter by account code (partial match)
            name (str): Filter by account name (partial match)
            account_type (str): Filter by account type
            limit (int): Maximum number of records to return (default: 100, max: 500)
            offset (int): Number of records to skip (default: 0)

        Returns:
            dict: Response with matching accounts
        """
        try:
            # Validate input parameters
            try:
                limit = max(1, min(int(limit), 500))  # Clamp between 1-500
                offset = max(0, int(offset))
            except (ValueError, TypeError):
                return {
                    "status": "error",
                    "error": "Invalid pagination parameters",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            _logger.info("API request: POST /api/v1/accounts/search")

            # Build search domain
            domain = []
            if code:
                domain.append(("code", "ilike", code))
            if name:
                domain.append(("name", "ilike", name))
            if account_type:
                domain.append(("account_type", "=", account_type))

            # Get accounts
            Account = request.env["account.account"].sudo()
            total_count = Account.search_count(domain)
            accounts = Account.search(domain, limit=limit, offset=offset, order="code ASC")

            # Convert to list of dicts
            accounts_data = [self._get_account_data(acc) for acc in accounts]

            response = {
                "status": "success",
                "data": accounts_data,
                "metadata": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "count": len(accounts_data),
                    "filters": {"code": code, "name": name, "account_type": account_type},
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            _logger.info(f"API response: {len(accounts_data)} accounts found")
            return response

        except Exception as e:
            _logger.error(f"Error in search_accounts: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e), "timestamp": datetime.utcnow().isoformat()}

    @http.route("/api/v1/accounts/types", type="json", auth="user", methods=["GET"], csrf=False)
    def get_account_types(self, **kwargs):
        """
        Get list of available account types.

        Returns:
            dict: Response with account types
        """
        try:
            _logger.info("API request: GET /api/v1/accounts/types")

            # Get unique account types efficiently using read_group
            Account = request.env["account.account"].sudo()
            groups = Account.read_group(
                domain=[], fields=["account_type"], groupby=["account_type"]
            )
            account_types = [g["account_type"] for g in groups if g.get("account_type")]

            response = {
                "status": "success",
                "data": sorted(account_types),
                "metadata": {"count": len(account_types)},
                "timestamp": datetime.utcnow().isoformat(),
            }

            _logger.info(f"API response: {len(account_types)} account types")
            return response

        except Exception as e:
            _logger.error(f"Error in get_account_types: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e), "timestamp": datetime.utcnow().isoformat()}

    @http.route("/api/v1/accounts/stats", type="json", auth="user", methods=["GET"], csrf=False)
    def get_account_stats(self, **kwargs):
        """
        Get accounting accounts statistics.

        Returns:
            dict: Response with statistics
        """
        try:
            _logger.info("API request: GET /api/v1/accounts/stats")

            Account = request.env["account.account"].sudo()

            # Total accounts
            total_accounts = Account.search_count([])

            # Group by account type using read_group for efficiency
            type_groups = Account.read_group(
                domain=[], fields=["account_type"], groupby=["account_type"]
            )
            type_counts = {
                g["account_type"] or "unspecified": g["account_type_count"] for g in type_groups
            }

            # Group by internal group using read_group
            group_groups = Account.read_group(
                domain=[], fields=["internal_group"], groupby=["internal_group"]
            )
            group_counts = {
                g["internal_group"] or "unspecified": g["internal_group_count"]
                for g in group_groups
            }

            # Counts for specific attributes
            reconcilable_count = Account.search_count([("reconcile", "=", True)])
            deprecated_count = Account.search_count([("deprecated", "=", True)])

            response = {
                "status": "success",
                "data": {
                    "total_accounts": total_accounts,
                    "by_type": type_counts,
                    "by_internal_group": group_counts,
                    "reconcilable_count": reconcilable_count,
                    "deprecated_count": deprecated_count,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            _logger.info(f"API response: Stats for {total_accounts} accounts")
            return response

        except Exception as e:
            _logger.error(f"Error in get_account_stats: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e), "timestamp": datetime.utcnow().isoformat()}
