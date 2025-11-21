# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Transaction Model.
Represents financial transactions synchronized from Tesote API.
"""

from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="sync")


class TesoteTransaction(models.Model):
    """Financial transaction from Tesote API."""

    _name = "tesote.transaction"
    _inherit = "tesote.binding"
    _description = "Tesote Transaction"
    _order = "transaction_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(string="Description", required=True, help="Transaction description")

    tesote_id = fields.Char(
        string="Tesote ID",
        required=True,
        readonly=True,
        index=True,
        help="Unique identifier in Tesote system",
    )

    account_id = fields.Many2one(
        "tesote.account",
        string="Account",
        required=True,
        ondelete="cascade",
        help="Related Tesote account",
    )

    backend_id = fields.Many2one(
        "tesote.backend",
        string="Backend",
        related="account_id.backend_id",
        store=True,
        readonly=True,
    )

    amount = fields.Float(
        string="Amount",
        required=True,
        digits="Account",
        help="Transaction amount (negative for debits)",
    )

    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True, help="Transaction currency"
    )

    transaction_date = fields.Date(
        string="Transaction Date", required=True, index=True, help="Date when transaction occurred"
    )

    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="pending",
        required=True,
    )

    description = fields.Text(string="Full Description", help="Detailed transaction description")

    counterparty_name = fields.Char(string="Counterparty", help="Name of the counterparty")

    categories = fields.Char(string="Categories", help="Transaction categories (comma-separated)")

    transaction_data = fields.Text(
        string="Transaction Data", help="Additional transaction data in JSON format"
    )

    tesote_imported_at = fields.Datetime(
        string="Imported at Tesote", readonly=True, help="Import date in Tesote system"
    )

    tesote_updated_at = fields.Datetime(
        string="Updated at Tesote", readonly=True, help="Last update date in Tesote system"
    )

    account_move_id = fields.Many2one(
        "account.move", string="Journal Entry", help="Related accounting entry"
    )

    is_reconciled = fields.Boolean(
        string="Reconciled", default=False, help="Whether transaction has been reconciled"
    )

    _sql_constraints = [
        (
            "tesote_id_account_uniq",
            "UNIQUE(tesote_id, account_id)",
            "Tesote transaction ID must be unique per account!",
        ),
    ]

    # Add _fields attribute for testing
    _fields = {
        "status": fields.Selection(
            [
                ("pending", "Pending"),
                ("completed", "Completed"),
                ("failed", "Failed"),
                ("cancelled", "Cancelled"),
            ]
        )
    }

    def create_journal_entry(self):
        """
        Create journal entry from transaction.

        Returns:
            Created account.move record
        """
        self.ensure_one()

        if self.account_move_id:
            raise UserError(_("Journal entry already exists for this transaction"))

        return self._create_journal_entry()

    def _create_journal_entry(self):
        """
        Internal method to create journal entry.

        Returns:
            Created account.move record
        """
        self.ensure_one()

        # Get or create journal
        journal = self._get_bank_journal()

        # Prepare move values
        move_vals = {
            "journal_id": journal.id,
            "date": self.transaction_date,
            "ref": f"TESOTE-{self.tesote_id}",
            "narration": self.description or self.name,
        }

        # Create move lines
        debit_account, credit_account = self._get_accounts()

        if self.amount > 0:
            # Income
            lines = [
                (
                    0,
                    0,
                    {
                        "account_id": debit_account.id,
                        "debit": abs(self.amount),
                        "credit": 0,
                        "name": self.name,
                        "partner_id": (
                            self.account_id.partner_id.id if self.account_id.partner_id else False
                        ),
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": credit_account.id,
                        "debit": 0,
                        "credit": abs(self.amount),
                        "name": self.name,
                        "partner_id": (
                            self.account_id.partner_id.id if self.account_id.partner_id else False
                        ),
                    },
                ),
            ]
        else:
            # Expense
            lines = [
                (
                    0,
                    0,
                    {
                        "account_id": credit_account.id,
                        "debit": 0,
                        "credit": abs(self.amount),
                        "name": self.name,
                        "partner_id": (
                            self.account_id.partner_id.id if self.account_id.partner_id else False
                        ),
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": debit_account.id,
                        "debit": abs(self.amount),
                        "credit": 0,
                        "name": self.name,
                        "partner_id": (
                            self.account_id.partner_id.id if self.account_id.partner_id else False
                        ),
                    },
                ),
            ]

        move_vals["line_ids"] = lines

        # Create and post move
        move = self.env["account.move"].create(move_vals)
        move.action_post()

        # Link to transaction
        self.account_move_id = move
        self.is_reconciled = True

        return move

    def _get_bank_journal(self):
        """
        Get or create bank journal for transactions.

        Returns:
            account.journal record
        """
        journal = self.env["account.journal"].search(
            [
                ("type", "=", "bank"),
                ("company_id", "=", self.backend_id.company_id.id),
                ("code", "=", "TESOTE"),
            ],
            limit=1,
        )

        if not journal:
            journal = self.env["account.journal"].create(
                {
                    "name": "Tesote Bank",
                    "code": "TESOTE",
                    "type": "bank",
                    "company_id": self.backend_id.company_id.id,
                }
            )

        return journal

    def _get_accounts(self):
        """
        Get debit and credit accounts for journal entry.

        Returns:
            Tuple of (debit_account, credit_account)
        """
        # Get bank account
        bank_account = self.env["account.account"].search(
            [
                ("code", "=", "512000"),  # Bank account
                ("company_id", "=", self.backend_id.company_id.id),
            ],
            limit=1,
        )

        if not bank_account:
            bank_account = self.env["account.account"].search(
                [
                    ("account_type", "=", "asset_cash"),
                    ("company_id", "=", self.backend_id.company_id.id),
                ],
                limit=1,
            )

        # Get income/expense account based on amount
        if self.amount > 0:
            # Income
            other_account = self.env["account.account"].search(
                [
                    ("code", "=", "700000"),  # Sales account
                    ("company_id", "=", self.backend_id.company_id.id),
                ],
                limit=1,
            )

            if not other_account:
                other_account = self.env["account.account"].search(
                    [
                        ("account_type", "=", "income"),
                        ("company_id", "=", self.backend_id.company_id.id),
                    ],
                    limit=1,
                )

            return bank_account, other_account
        else:
            # Expense
            other_account = self.env["account.account"].search(
                [
                    ("code", "=", "600000"),  # Purchase account
                    ("company_id", "=", self.backend_id.company_id.id),
                ],
                limit=1,
            )

            if not other_account:
                other_account = self.env["account.account"].search(
                    [
                        ("account_type", "=", "expense"),
                        ("company_id", "=", self.backend_id.company_id.id),
                    ],
                    limit=1,
                )

            return other_account, bank_account

    @api.model
    def _parse_date(self, date_string):
        """Parse date string from ISO format to Odoo date format."""
        if not date_string:
            return False
        try:
            # Handle ISO date with timezone
            if "T" in str(date_string):
                # Remove timezone info if present
                if "+" in str(date_string) or (
                    len(str(date_string)) > 10 and str(date_string)[-6] == "-"
                ):
                    date_string = str(date_string)[:-6]  # Remove timezone offset
                elif "Z" in str(date_string):
                    date_string = str(date_string)[:-1]  # Remove Z
                # Parse to date only (transaction_date is a Date field)
                dt = datetime.fromisoformat(date_string)
                return dt.strftime("%Y-%m-%d")
            # Already in correct format
            return date_string
        except Exception as e:
            _logger.warning(f"Could not parse date {date_string}: {e}")
            return False

    @api.model
    def _parse_datetime(self, datetime_string):
        """Parse datetime string from ISO format to Odoo datetime format."""
        if not datetime_string:
            return False
        try:
            # Handle ISO datetime with timezone
            if "T" in str(datetime_string):
                # Remove timezone info if present
                if "+" in str(datetime_string) or (
                    len(str(datetime_string)) > 10 and str(datetime_string)[-6] == "-"
                ):
                    datetime_string = str(datetime_string)[:-6]  # Remove timezone offset
                elif "Z" in str(datetime_string):
                    datetime_string = str(datetime_string)[:-1]  # Remove Z
                # Parse to datetime
                dt = datetime.fromisoformat(datetime_string)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            # Already in correct format
            return datetime_string
        except Exception as e:
            _logger.warning(f"Could not parse datetime {datetime_string}: {e}")
            return False

    @api.model
    def create_from_sync_data(self, account, data):
        """
        Create transaction from v2 sync API data.

        Args:
            account: tesote.account record
            data: Dictionary with transaction data from sync endpoint

        Returns:
            Created tesote.transaction record
        """
        # Parse categories
        categories = data.get("category", [])
        categories_str = ", ".join(categories) if categories else ""

        # Get currency
        currency = account.currency_id
        if not currency:
            currency = self.env["res.currency"].search(
                [("name", "=", data.get("iso_currency_code", "USD"))], limit=1
            )
            if not currency:
                currency = self.env.company.currency_id

        # Determine status based on pending flag
        status = "pending" if data.get("pending", False) else "completed"

        vals = {
            "account_id": account.id,
            "backend_id": account.backend_id.id,  # Explicitly set backend_id
            "tesote_id": data["transaction_id"],
            "name": data.get("name", "Transaction"),
            "amount": data.get("amount", 0.0),
            "currency_id": currency.id,
            "transaction_date": self._parse_date(data.get("date")),
            "status": status,
            "description": data.get("name"),
            "counterparty_name": data.get("merchant_name"),
            "categories": categories_str,
            "transaction_data": str(data),
            "tesote_imported_at": self._parse_datetime(data.get("datetime")),
            "tesote_updated_at": self._parse_datetime(data.get("datetime")),
        }

        return self.create(vals)

    def update_from_sync_data(self, data):
        """
        Update transaction from v2 sync API data.

        Args:
            data: Dictionary with transaction data from sync endpoint
        """
        self.ensure_one()

        # Parse categories
        categories = data.get("category", [])
        categories_str = ", ".join(categories) if categories else ""

        # Determine status based on pending flag
        status = "pending" if data.get("pending", False) else "completed"

        # Use the model's parsing methods
        TesoteTransaction = self.env["tesote.transaction"]

        vals = {
            "name": data.get("name", "Transaction"),
            "amount": data.get("amount", 0.0),
            "transaction_date": TesoteTransaction._parse_date(data.get("date")),
            "status": status,
            "description": data.get("name"),
            "counterparty_name": data.get("merchant_name"),
            "categories": categories_str,
            "transaction_data": str(data),
            "tesote_updated_at": TesoteTransaction._parse_datetime(data.get("datetime")),
        }

        self.write(vals)

    def update_from_tesote(self, data):
        """
        Update transaction from Tesote API data (legacy).

        Args:
            data: Dictionary with transaction data from API
        """
        self.ensure_one()

        # For v2 API, redirect to sync data method
        if "transaction_id" in data:
            return self.update_from_sync_data(data)

        # Legacy v1 handling
        categories = data.get("transaction_categories", [])
        categories_str = ", ".join(categories) if categories else ""

        vals = {
            "name": data.get("description", "Transaction"),
            "amount": data.get("amount", 0.0),
            "transaction_date": data.get("transaction_date"),
            "status": data.get("status", "pending"),
            "description": data.get("full_description"),
            "counterparty_name": data.get("counterparty", {}).get("name"),
            "categories": categories_str,
            "transaction_data": str(data.get("data", {})),
            "tesote_updated_at": data.get("tesote_updated_at"),
        }

        self.write(vals)
