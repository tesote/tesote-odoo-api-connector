# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Account Model.
Represents financial accounts synchronized from Tesote API.
"""

from datetime import datetime

from odoo import _, api, fields, models

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="sync")


class TesoteAccount(models.Model):
    """Financial account from Tesote API."""

    _name = "tesote.account"
    _inherit = "tesote.binding"
    _description = "Tesote Account"
    _rec_name = "name"

    name = fields.Char(string="Account Name", required=True, help="Display name of the account")

    tesote_id = fields.Char(
        string="Tesote ID",
        required=True,
        readonly=True,
        index=True,
        help="Unique identifier in Tesote system",
    )

    backend_id = fields.Many2one(
        "tesote.backend",
        string="Backend",
        required=True,
        ondelete="cascade",
        help="Tesote backend instance",
    )

    partner_id = fields.Many2one("res.partner", string="Partner", help="Linked partner/customer")

    transaction_count = fields.Integer(
        string="Transaction Count", compute="_compute_transaction_count", store=False
    )

    @api.depends("transaction_ids")
    def _compute_transaction_count(self):
        """Compute transaction count."""
        for account in self:
            account.transaction_count = len(account.transaction_ids)

    bank_name = fields.Char(string="Bank Name", help="Name of the financial institution")

    legal_entity_name = fields.Char(string="Legal Entity", help="Legal entity owning the account")

    account_data = fields.Text(string="Account Data", help="Additional account data in JSON format")

    balance = fields.Float(string="Balance", digits="Account", help="Current account balance")

    currency_id = fields.Many2one("res.currency", string="Currency", help="Account currency")

    tesote_created_at = fields.Datetime(
        string="Created in Tesote", readonly=True, help="Creation date in Tesote system"
    )

    tesote_updated_at = fields.Datetime(
        string="Updated in Tesote", readonly=True, help="Last update date in Tesote system"
    )

    balance_data_current_as_of = fields.Datetime(
        string="Balance As Of",
        readonly=True,
        help="Timestamp when balance data was last updated in Tesote",
    )

    transaction_ids = fields.One2many("tesote.transaction", "account_id", string="Transactions")

    sync_cursor = fields.Char(string="Sync Cursor", help="Cursor for incremental transaction sync")

    sync_date = fields.Datetime(string="Last Sync", help="Last successful transaction sync date")

    active = fields.Boolean(string="Active", default=True)

    # Link to Odoo accounting account
    odoo_account_id = fields.Many2one(
        "account.account",
        string="Odoo Account",
        help="Odoo accounting account linked to this Tesote account for journal entries",
        domain="[('account_type', 'in', ['asset_cash', 'liability_credit_card', 'asset_current'])]",
    )

    _sql_constraints = [
        (
            "tesote_id_backend_uniq",
            "UNIQUE(tesote_id, backend_id)",
            "Tesote ID must be unique per backend!",
        ),
    ]

    def sync_from_tesote(self):
        """
        Synchronize account data from Tesote API.

        Fetches latest account information and updates local record.
        """
        self.ensure_one()

        # For now, just update from API
        from ..components.adapter import TesoteAdapter

        adapter = TesoteAdapter(self.backend_id)

        # Get account data from API
        account_data = adapter.get_account(self.tesote_id)
        if account_data:
            self.update_from_tesote(account_data)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Account synchronized successfully"),
                "type": "success",
                "sticky": False,
            },
        }

    def import_transactions(self, date_from=None, date_to=None):
        """
        Import transactions for this account.

        Args:
            date_from: Start date for import
            date_to: End date for import
        """
        self.ensure_one()

        return self.backend_id.import_transactions(
            account_ids=[self.id], date_from=date_from, date_to=date_to
        )

    def action_view_transactions(self):
        """
        Open view to display account transactions.

        Returns:
            Action dictionary to open transaction list
        """
        self.ensure_one()

        return {
            "name": _("Transactions"),
            "type": "ir.actions.act_window",
            "res_model": "tesote.transaction",
            "view_mode": "list,form",
            "domain": [("account_id", "=", self.id)],
            "context": {
                "default_account_id": self.id,
            },
        }

    def sync_balance_to_odoo(self):
        """
        Sync Tesote account balance to linked Odoo account.

        Creates an adjustment journal entry if there's a difference between
        the Tesote balance and the Odoo account balance.

        Returns:
            account.move record if adjustment was created, False otherwise
        """
        self.ensure_one()

        # Check if account is mapped to Odoo
        if not self.odoo_account_id:
            _logger.debug(f"Account {self.name} not mapped to Odoo account, skipping balance sync")
            return False

        # Check if suspense account is configured
        if not self.backend_id.suspense_account_id:
            _logger.warning(
                f"Suspense account not configured on backend, skipping balance sync for {self.name}"
            )
            return False

        # Get current Odoo account balance (sum of debits - credits)
        odoo_balance = self.odoo_account_id.current_balance or 0.0

        # Get Tesote balance (already stored on this record)
        tesote_balance = self.balance or 0.0

        # Calculate difference
        difference = tesote_balance - odoo_balance

        # Skip if no difference (within small tolerance for floating point)
        if abs(difference) < 0.01:
            _logger.debug(
                f"Account {self.name} balance already matches: "
                f"Tesote={tesote_balance}, Odoo={odoo_balance}"
            )
            return False

        _logger.info(
            f"Creating balance adjustment for {self.name}: "
            f"Tesote={tesote_balance}, Odoo={odoo_balance}, Adjustment={difference}"
        )

        # Create adjustment journal entry
        return self._create_balance_adjustment(difference)

    def _create_balance_adjustment(self, amount):
        """
        Create a journal entry to adjust the Odoo account balance.

        Args:
            amount: The adjustment amount (positive = increase, negative = decrease)

        Returns:
            Created account.move record
        """
        self.ensure_one()

        # Get or create journal for adjustments
        journal = self._get_adjustment_journal()

        # Prepare move values
        move_vals = {
            "journal_id": journal.id,
            "date": fields.Date.today(),
            "ref": f"TESOTE-BAL-{self.tesote_id}",
            "narration": _(
                "Balance adjustment for Tesote account %(account)s",
                account=self.name,
            ),
        }

        # Create move lines
        bank_account = self.odoo_account_id
        suspense_account = self.backend_id.suspense_account_id

        if amount > 0:
            # Need to increase bank balance: Debit bank, Credit suspense
            lines = [
                (
                    0,
                    0,
                    {
                        "account_id": bank_account.id,
                        "debit": abs(amount),
                        "credit": 0,
                        "name": _("Tesote balance adjustment"),
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": suspense_account.id,
                        "debit": 0,
                        "credit": abs(amount),
                        "name": _("Tesote balance adjustment"),
                    },
                ),
            ]
        else:
            # Need to decrease bank balance: Credit bank, Debit suspense
            lines = [
                (
                    0,
                    0,
                    {
                        "account_id": bank_account.id,
                        "debit": 0,
                        "credit": abs(amount),
                        "name": _("Tesote balance adjustment"),
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": suspense_account.id,
                        "debit": abs(amount),
                        "credit": 0,
                        "name": _("Tesote balance adjustment"),
                    },
                ),
            ]

        move_vals["line_ids"] = lines

        # Create and post the journal entry
        move = self.env["account.move"].create(move_vals)
        move.action_post()

        _logger.info(f"Created balance adjustment journal entry {move.name} for {self.name}")

        return move

    def _get_adjustment_journal(self):
        """
        Get or create journal for balance adjustments.

        Returns:
            account.journal record
        """
        journal = self.env["account.journal"].search(
            [
                ("type", "=", "general"),
                ("company_id", "=", self.backend_id.company_id.id),
                ("code", "=", "TSADJ"),
            ],
            limit=1,
        )

        if not journal:
            journal = self.env["account.journal"].create(
                {
                    "name": "Tesote Adjustments",
                    "code": "TSADJ",
                    "type": "general",
                    "company_id": self.backend_id.company_id.id,
                }
            )
            _logger.info("Created Tesote Adjustments journal")

        return journal

    @api.model
    def _parse_tesote_datetime(self, date_string):
        """
        Parse Tesote API datetime string to Odoo format.
        Handles ISO format with timezone: 2025-03-05T09:41:36-05:00
        """
        if not date_string:
            return False
        try:
            # Parse ISO format with timezone
            if "T" in date_string:
                # Remove timezone info for Odoo
                if "+" in date_string or date_string[-6] == "-":
                    date_string = date_string[:-6]  # Remove timezone offset
                elif "Z" in date_string:
                    date_string = date_string[:-1]  # Remove Z
                # Convert to Odoo datetime format
                dt = datetime.fromisoformat(date_string)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            return date_string
        except Exception as e:
            _logger.warning(f"Could not parse date {date_string}: {e}")
            return False

    @api.model
    def create_from_tesote(self, backend, data):
        """
        Create account from Tesote API data.

        Args:
            backend: tesote.backend record
            data: Dictionary with account data from API

        Returns:
            Created tesote.account record
        """
        # DEBUG: Log full API response to diagnose missing balance
        _logger.info(f"Creating account from API data: {data}")
        _logger.info(
            f"Balance fields in response - balance_cents: {data.get('balance_cents')}, "
            f"available_balance_cents: {data.get('available_balance_cents')}"
        )

        vals = {
            "backend_id": backend.id,
            "tesote_id": data["id"],
            "name": data["name"],
            "bank_name": data.get("bank", {}).get("name"),
            "legal_entity_name": data.get("legal_entity", {}).get("name"),
            "account_data": str(data.get("data", {})),
            "tesote_created_at": self._parse_tesote_datetime(data.get("tesote_created_at")),
            "tesote_updated_at": self._parse_tesote_datetime(data.get("tesote_updated_at")),
        }

        # Set balance if available - API returns balance_cents in nested 'data' field
        # Try nested data field first (API v2 structure), then fallback to root level
        nested_data = data.get("data", {})
        balance_cents = nested_data.get("balance_cents") or nested_data.get(
            "available_balance_cents"
        )

        # Fallback to root level if not in nested data
        if balance_cents is None:
            balance_cents = data.get("balance_cents") or data.get("available_balance_cents")

        if balance_cents is not None:
            # Handle both string and numeric values
            balance_cents_num = (
                float(balance_cents) if isinstance(balance_cents, str) else balance_cents
            )
            vals["balance"] = balance_cents_num / 100.0
            _logger.info(f"Converted balance: {balance_cents} cents -> ${vals['balance']}")
        else:
            _logger.warning(
                f"No balance data in API response for account {data.get('id')}. "
                f"Checked both nested data.balance_cents and root balance_cents fields."
            )

        # Store balance timestamp if available - check nested data first
        balance_timestamp = nested_data.get("balance_data_current_as_of") or data.get(
            "balance_data_current_as_of"
        )
        if balance_timestamp:
            vals["balance_data_current_as_of"] = self._parse_tesote_datetime(balance_timestamp)

        # Set currency if available - check nested data first
        currency_code = nested_data.get("currency") or data.get("currency")
        if currency_code:
            # Search including inactive currencies
            currency = (
                self.env["res.currency"]
                .with_context(active_test=False)
                .search([("name", "=", currency_code)], limit=1)
            )
            if currency:
                vals["currency_id"] = currency.id
                # Auto-activate currency for invoicing if it's inactive
                if not currency.active:
                    currency.active = True
                    _logger.info(f"Auto-activated currency {currency_code} for invoicing")

        return self.create(vals)

    def update_from_tesote(self, data):
        """
        Update account from Tesote API data.

        Args:
            data: Dictionary with account data from API
        """
        self.ensure_one()

        # DEBUG: Log full API response to diagnose missing balance
        _logger.info(f"Updating account {self.tesote_id} from API data: {data}")
        _logger.info(
            f"Balance fields in response - balance_cents: {data.get('balance_cents')}, "
            f"available_balance_cents: {data.get('available_balance_cents')}"
        )

        vals = {
            "name": data["name"],
            "bank_name": data.get("bank", {}).get("name"),
            "legal_entity_name": data.get("legal_entity", {}).get("name"),
            "account_data": str(data.get("data", {})),
            "tesote_updated_at": self._parse_tesote_datetime(data.get("tesote_updated_at")),
        }

        # Update balance if available - API returns balance_cents in nested 'data' field
        # Try nested data field first (API v2 structure), then fallback to root level
        nested_data = data.get("data", {})
        balance_cents = nested_data.get("balance_cents") or nested_data.get(
            "available_balance_cents"
        )

        # Fallback to root level if not in nested data
        if balance_cents is None:
            balance_cents = data.get("balance_cents") or data.get("available_balance_cents")

        if balance_cents is not None:
            # Handle both string and numeric values
            balance_cents_num = (
                float(balance_cents) if isinstance(balance_cents, str) else balance_cents
            )
            vals["balance"] = balance_cents_num / 100.0
            _logger.info(f"Converted balance: {balance_cents} cents -> ${vals['balance']}")
        else:
            _logger.warning(
                f"No balance data in API response for account {data.get('id')}. "
                f"Checked both nested data.balance_cents and root balance_cents fields."
            )

        # Update balance timestamp if available - check nested data first
        balance_timestamp = nested_data.get("balance_data_current_as_of") or data.get(
            "balance_data_current_as_of"
        )
        if balance_timestamp:
            vals["balance_data_current_as_of"] = self._parse_tesote_datetime(balance_timestamp)

        # Update currency if available - check nested data first
        currency_code = nested_data.get("currency") or data.get("currency")
        if currency_code:
            # Search including inactive currencies
            currency = (
                self.env["res.currency"]
                .with_context(active_test=False)
                .search([("name", "=", currency_code)], limit=1)
            )
            if currency:
                vals["currency_id"] = currency.id
                # Auto-activate currency for invoicing if it's inactive
                if not currency.active:
                    currency.active = True
                    _logger.info(f"Auto-activated currency {currency_code} for invoicing")

        self.write(vals)
