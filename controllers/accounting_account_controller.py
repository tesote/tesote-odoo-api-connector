import json

from odoo import http
from odoo.http import request

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="api")


class AccountingAccountController(http.Controller):
    """RESTful API controller for Odoo accounting accounts."""

    @http.route("/api/accounting_accounts", type="http", auth="user", methods=["GET"], csrf=False)
    def index(self, **kwargs):
        """
        GET /api/accounting_accounts - List all accounting accounts.

        Returns:
            JSON array of accounting account objects with id, code, name, account_type, etc.
        """
        try:
            accounting_accounts = request.env["account.account"].search([])

            accounting_account_data = []
            for accounting_account in accounting_accounts:
                accounting_account_data.append(
                    self._serialize_accounting_account(accounting_account)
                )

            return self._json_response({"accounting_accounts": accounting_account_data})

        except Exception as e:
            _logger.error(f"Error fetching accounting accounts: {e}", exc_info=True)
            return self._json_response({"error": str(e)}, status=500)

    @http.route(
        "/api/accounting_accounts/<int:accounting_account_id>",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def show(self, accounting_account_id, **kwargs):
        """
        GET /api/accounting_accounts/:id - Show a single accounting account.

        Args:
            accounting_account_id: Odoo account.account ID

        Returns:
            JSON object with accounting account details
        """
        try:
            accounting_account = request.env["account.account"].browse(accounting_account_id)

            if not accounting_account.exists():
                return self._json_response(
                    {"error": f"Accounting account {accounting_account_id} not found"},
                    status=404,
                )

            return self._json_response(
                {"accounting_account": self._serialize_accounting_account(accounting_account)}
            )

        except Exception as e:
            _logger.error(
                f"Error fetching accounting account {accounting_account_id}: {e}", exc_info=True
            )
            return self._json_response({"error": str(e)}, status=500)

    def _serialize_accounting_account(self, accounting_account):
        """
        Serialize an account.account record to JSON-friendly dict.

        Args:
            accounting_account: account.account record

        Returns:
            dict with accounting account data
        """
        return {
            "id": accounting_account.id,
            "code": accounting_account.code,
            "name": accounting_account.name,
            "account_type": accounting_account.account_type,
            "currency_id": (
                accounting_account.currency_id.id if accounting_account.currency_id else None
            ),
            "currency_code": (
                accounting_account.currency_id.name if accounting_account.currency_id else None
            ),
            "company_id": accounting_account.company_id.id,
            "company_name": accounting_account.company_id.name,
            "reconcile": accounting_account.reconcile,
            "deprecated": (
                accounting_account.deprecated
                if hasattr(accounting_account, "deprecated")
                else False
            ),
        }

    def _json_response(self, data, status=200):
        """
        Create a JSON HTTP response.

        Args:
            data: Dictionary to serialize as JSON
            status: HTTP status code

        Returns:
            Odoo HTTP response object
        """
        return request.make_response(
            json.dumps(data, indent=2),
            status=status,
            headers=[("Content-Type", "application/json")],
        )
