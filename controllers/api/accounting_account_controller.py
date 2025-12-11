from odoo import _, http
from odoo.http import request

# Handle both package and direct imports for testing
try:
    from ...utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

try:
    from ...utils.sentry_config import capture_exception
except ImportError:
    from utils.sentry_config import capture_exception

try:
    from .base_controller import BaseApiController
except ImportError:
    from controllers.api.base_controller import BaseApiController

_logger = get_logger(__name__, category="api")


class AccountingAccountController(BaseApiController):
    """RESTful API controller for Odoo accounting accounts."""

    @http.route(
        "/tesote/api/accounting_accounts", type="http", auth="public", methods=["GET"], csrf=False
    )
    def index(self, **kwargs):
        """
        GET /tesote/api/accounting_accounts - List all accounting accounts.

        Requires authentication via X-Tesote-Signature and X-Tesote-Timestamp headers.

        Returns:
            JSON array of accounting account objects with id, code, name, account_type, etc.
        """
        is_authenticated, error_response = self._authenticate_request()
        if not is_authenticated:
            return error_response

        try:
            accounting_accounts = request.env["account.account"].sudo().search([])

            accounting_account_data = []
            for accounting_account in accounting_accounts:
                accounting_account_data.append(
                    self._serialize_accounting_account(accounting_account)
                )

            return self._json_response({"accounting_accounts": accounting_account_data})

        except Exception as e:
            _logger.error("Error fetching accounting accounts", exc_info=True)
            capture_exception(e)
            return self._json_response({"error": _("Internal server error")}, status=500)

    @http.route(
        "/tesote/api/accounting_accounts/<int:accounting_account_id>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def show(self, accounting_account_id, **kwargs):
        """
        GET /tesote/api/accounting_accounts/:id - Show a single accounting account.

        Requires authentication via X-Tesote-Signature and X-Tesote-Timestamp headers.

        Args:
            accounting_account_id: Odoo account.account ID

        Returns:
            JSON object with accounting account details
        """
        is_authenticated, error_response = self._authenticate_request()
        if not is_authenticated:
            return error_response

        try:
            accounting_account = request.env["account.account"].sudo().browse(accounting_account_id)

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
                "Error fetching accounting account %s", accounting_account_id, exc_info=True
            )
            capture_exception(e)
            return self._json_response({"error": _("Internal server error")}, status=500)

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
