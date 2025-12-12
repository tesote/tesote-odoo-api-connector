"""
Accounting Accounts API v1 Controller.

Provides versioned REST API at /tesote/api/v1/accounting/accounts
with cursor-based pagination and service layer architecture.
"""

import json
from datetime import datetime, timezone

from odoo import _, http
from odoo.http import request

try:
    from ....services import get_accounting_service
    from ....utils.colored_logger import get_logger
    from ....utils.sentry_config import capture_exception
    from ..base_controller import BaseApiController
except ImportError:
    from controllers.api.base_controller import BaseApiController
    from services import get_accounting_service
    from utils.colored_logger import get_logger
    from utils.sentry_config import capture_exception

_logger = get_logger(__name__, category="api")


class AccountingAccountsV1Controller(BaseApiController):
    """
    Accounting accounts API v1 controller.

    Inherits authentication from BaseApiController.
    Uses service layer for ERP abstraction.
    Implements cursor-based pagination.
    """

    @http.route(
        "/tesote/api/v1/accounting/accounts",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def list_accounts(self, cursor=None, limit=100, **kwargs):
        """
        GET /tesote/api/v1/accounting/accounts - List accounts with cursor pagination.

        Query parameters:
            cursor (str): Last seen ID for pagination (optional)
            limit (int): Max records (default: 100, max: 500)

        Returns:
            JSON with accounts, next_cursor, has_more

        Example:
            GET /tesote/api/v1/accounting/accounts?limit=10
            GET /tesote/api/v1/accounting/accounts?cursor=100&limit=10
        """
        # Authenticate (inherited from BaseApiController)
        is_authenticated, error_response = self._authenticate_request()
        if not is_authenticated:
            return error_response

        try:
            # Validate limit
            limit = self._validate_limit(limit)

            # Get service (ERP-agnostic)
            service = get_accounting_service(erp_type="odoo", env=request.env)

            # Get accounts with cursor pagination
            accounts, next_cursor, has_more = service.get_accounts(cursor=cursor, limit=limit)

            response = {
                "status": "success",
                "data": accounts,
                "metadata": {
                    "next_cursor": next_cursor,
                    "has_more": has_more,
                    "count": len(accounts),
                    "limit": limit,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            _logger.info(f"API v1: Listed {len(accounts)} accounts (cursor={cursor})")
            return self._json_response(response)

        except ValueError as e:
            _logger.warning(f"Validation error: {str(e)}")
            return self._json_response(
                {"status": "error", "error_code": "VALIDATION001", "error": str(e)}, status=400
            )
        except Exception as e:
            _logger.error(f"Error listing accounts: {str(e)}", exc_info=True)
            capture_exception(e)
            return self._json_response(
                {
                    "status": "error",
                    "error_code": "SERVER001",
                    "error": _("Internal server error"),
                },
                status=500,
            )

    @http.route(
        "/tesote/api/v1/accounting/accounts/<int:account_id>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def get_account(self, account_id, **kwargs):
        """
        GET /tesote/api/v1/accounting/accounts/:id - Get single account.

        Args:
            account_id: Account ID

        Returns:
            JSON with account data

        Example:
            GET /tesote/api/v1/accounting/accounts/123
        """
        # Authenticate
        is_authenticated, error_response = self._authenticate_request()
        if not is_authenticated:
            return error_response

        try:
            # Get service
            service = get_accounting_service(erp_type="odoo", env=request.env)

            # Get account
            account = service.get_account_by_id(str(account_id))

            if not account:
                return self._json_response(
                    {
                        "status": "error",
                        "error_code": "NOT_FOUND001",
                        "error": _("Account not found"),
                    },
                    status=404,
                )

            response = {
                "status": "success",
                "data": account,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            _logger.info(f"API v1: Retrieved account {account_id}")
            return self._json_response(response)

        except Exception as e:
            _logger.error(f"Error getting account {account_id}: {str(e)}", exc_info=True)
            capture_exception(e)
            return self._json_response(
                {
                    "status": "error",
                    "error_code": "SERVER001",
                    "error": _("Internal server error"),
                },
                status=500,
            )

    @http.route(
        "/tesote/api/v1/accounting/accounts/search",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def search_accounts(self, **kwargs):
        """
        POST /tesote/api/v1/accounting/accounts/search - Search accounts.

        Body (JSON):
            code (str): Account code filter (partial match)
            name (str): Account name filter (partial match)
            account_type (str): Account type (exact match)
            internal_group (str): Internal group (exact match)
            cursor (str): Pagination cursor
            limit (int): Max records (default: 100, max: 500)

        Returns:
            JSON with matching accounts

        Example:
            POST /tesote/api/v1/accounting/accounts/search
            {"code": "10", "limit": 10}
        """
        # Authenticate
        is_authenticated, error_response = self._authenticate_request()
        if not is_authenticated:
            return error_response

        try:
            # Parse JSON body
            try:
                body = json.loads(request.httprequest.data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self._json_response(
                    {
                        "status": "error",
                        "error_code": "VALIDATION001",
                        "error": _("Invalid JSON body"),
                    },
                    status=400,
                )

            # Extract and validate parameters
            code = body.get("code")
            name = body.get("name")
            account_type = body.get("account_type")
            internal_group = body.get("internal_group")
            cursor = body.get("cursor")
            limit = self._validate_limit(body.get("limit", 100))

            # Get service
            service = get_accounting_service(erp_type="odoo", env=request.env)

            # Search accounts
            accounts, next_cursor, has_more = service.search_accounts(
                code=code,
                name=name,
                account_type=account_type,
                internal_group=internal_group,
                cursor=cursor,
                limit=limit,
            )

            response = {
                "status": "success",
                "data": accounts,
                "metadata": {
                    "next_cursor": next_cursor,
                    "has_more": has_more,
                    "count": len(accounts),
                    "limit": limit,
                    "filters": {
                        "code": code,
                        "name": name,
                        "account_type": account_type,
                        "internal_group": internal_group,
                    },
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            _logger.info(f"API v1: Search found {len(accounts)} accounts")
            return self._json_response(response)

        except ValueError as e:
            _logger.warning(f"Validation error: {str(e)}")
            return self._json_response(
                {"status": "error", "error_code": "VALIDATION002", "error": str(e)}, status=400
            )
        except Exception as e:
            _logger.error(f"Error searching accounts: {str(e)}", exc_info=True)
            capture_exception(e)
            return self._json_response(
                {
                    "status": "error",
                    "error_code": "SERVER001",
                    "error": _("Internal server error"),
                },
                status=500,
            )

    @http.route(
        "/tesote/api/v1/accounting/accounts/types",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def get_types(self, **kwargs):
        """
        GET /tesote/api/v1/accounting/accounts/types - Get all account types.

        Returns:
            JSON with list of account types

        Example:
            GET /tesote/api/v1/accounting/accounts/types
        """
        # Authenticate
        is_authenticated, error_response = self._authenticate_request()
        if not is_authenticated:
            return error_response

        try:
            # Get service
            service = get_accounting_service(erp_type="odoo", env=request.env)

            # Get types
            types = service.get_account_types()

            response = {
                "status": "success",
                "data": sorted(types),
                "metadata": {"count": len(types)},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            _logger.info(f"API v1: Retrieved {len(types)} account types")
            return self._json_response(response)

        except Exception as e:
            _logger.error(f"Error getting account types: {str(e)}", exc_info=True)
            capture_exception(e)
            return self._json_response(
                {
                    "status": "error",
                    "error_code": "SERVER001",
                    "error": _("Internal server error"),
                },
                status=500,
            )

    @http.route(
        "/tesote/api/v1/accounting/accounts/stats",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def get_stats(self, **kwargs):
        """
        GET /tesote/api/v1/accounting/accounts/stats - Get account statistics.

        Returns:
            JSON with statistics

        Example:
            GET /tesote/api/v1/accounting/accounts/stats
        """
        # Authenticate
        is_authenticated, error_response = self._authenticate_request()
        if not is_authenticated:
            return error_response

        try:
            # Get service
            service = get_accounting_service(erp_type="odoo", env=request.env)

            # Get statistics
            stats = service.get_statistics()

            response = {
                "status": "success",
                "data": stats,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            _logger.info(f"API v1: Retrieved stats for {stats['total_accounts']} accounts")
            return self._json_response(response)

        except Exception as e:
            _logger.error(f"Error getting account stats: {str(e)}", exc_info=True)
            capture_exception(e)
            return self._json_response(
                {
                    "status": "error",
                    "error_code": "SERVER001",
                    "error": _("Internal server error"),
                },
                status=500,
            )
