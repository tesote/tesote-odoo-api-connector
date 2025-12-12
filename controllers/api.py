"""
API Controller for exposing Odoo accounting accounts as REST endpoints.

This module provides RESTful API endpoints for accessing accounting accounts data.
"""

from datetime import datetime

from odoo import http
from odoo.http import request

try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="api")


class AccountingAPIController(http.Controller):
    """RESTful API controller for accessing accounting accounts."""

    def _validate_authentication(self):
        """
        Validate API authentication.
        For now, using Odoo's built-in authentication.

        Returns:
            tuple: (success: bool, error_response: dict or None)
        """
        if not request.env.user or request.env.user.id == request.env.ref("base.public_user").id:
            return False, {
                "error": "Authentication required",
                "message": "Please provide valid credentials",
            }
        return True, None

    def _get_account_data(self, account):
        """
        Convert account record to dictionary.

        Args:
            account: account.account record

        Returns:
            dict: Account data
        """
        return {
            "id": account.id,
            "code": account.code,
            "name": account.name,
            "account_type": account.account_type,
            "internal_group": account.internal_group,
            "reconcile": account.reconcile,
            "deprecated": account.deprecated,
            "currency_id": account.currency_id.id if account.currency_id else None,
            "currency_code": account.currency_id.name if account.currency_id else None,
            "company_id": account.company_id.id,
            "company_name": account.company_id.name,
            "current_balance": account.current_balance,
            "allowed_journal_ids": [j.id for j in account.allowed_journal_ids],
            "tag_ids": [{"id": t.id, "name": t.name} for t in account.tag_ids],
            "note": account.note or "",
        }

    @http.route("/api/v1/accounts", type="json", auth="user", methods=["GET"], csrf=False)
    def get_accounts(self, limit=100, offset=0, domain=None, **kwargs):
        """
        Get list of accounting accounts.

        Query parameters:
            limit (int): Maximum number of records to return (default: 100)
            offset (int): Number of records to skip (default: 0)
            domain (list): Odoo domain filter (optional)

        Returns:
            dict: Response with accounts list and metadata
        """
        try:
            _logger.info(f"API request: GET /api/v1/accounts (limit={limit}, offset={offset})")

            # Parse domain
            search_domain = domain if domain else []

            # Get accounts
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
            limit (int): Maximum number of records to return (default: 100)
            offset (int): Number of records to skip (default: 0)

        Returns:
            dict: Response with matching accounts
        """
        try:
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

            # Get all unique account types
            Account = request.env["account.account"].sudo()
            accounts = Account.search([])
            account_types = list(set(acc.account_type for acc in accounts if acc.account_type))

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
            accounts = Account.search([])

            # Group by account type
            type_counts = {}
            for acc in accounts:
                acc_type = acc.account_type or "unspecified"
                type_counts[acc_type] = type_counts.get(acc_type, 0) + 1

            # Group by internal group
            group_counts = {}
            for acc in accounts:
                group = acc.internal_group or "unspecified"
                group_counts[group] = group_counts.get(group, 0) + 1

            response = {
                "status": "success",
                "data": {
                    "total_accounts": len(accounts),
                    "by_type": type_counts,
                    "by_internal_group": group_counts,
                    "reconcilable_count": len([a for a in accounts if a.reconcile]),
                    "deprecated_count": len([a for a in accounts if a.deprecated]),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            _logger.info(f"API response: Stats for {len(accounts)} accounts")
            return response

        except Exception as e:
            _logger.error(f"Error in get_account_stats: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e), "timestamp": datetime.utcnow().isoformat()}
