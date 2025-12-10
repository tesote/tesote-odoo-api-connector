# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Invoice Model.
Represents invoices synchronized from Tesote API.
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


class TesoteInvoice(models.Model):
    """Invoice from Tesote API."""

    _name = "tesote.invoice"
    _inherit = "tesote.binding"
    _description = "Tesote Invoice"
    _order = "invoice_date desc, id desc"
    _rec_name = "invoice_number"

    invoice_number = fields.Char(
        string="Invoice Number",
        required=True,
        help="External invoice number from Tesote",
    )

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

    # Invoice type
    invoice_type = fields.Selection(
        [
            ("customer_invoice", "Customer Invoice"),
            ("vendor_bill", "Vendor Bill"),
            ("credit_note", "Credit Note"),
            ("debit_note", "Debit Note"),
        ],
        string="Type",
        required=True,
        default="customer_invoice",
        help="Type of invoice",
    )

    # Dates
    invoice_date = fields.Date(
        string="Invoice Date",
        required=True,
        index=True,
        help="Date when invoice was issued",
    )

    due_date = fields.Date(
        string="Due Date",
        help="Payment due date",
    )

    # Amounts
    subtotal = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        help="Amount before taxes",
    )

    tax_amount = fields.Monetary(
        string="Tax Amount",
        currency_field="currency_id",
        help="Total tax amount",
    )

    total_amount = fields.Monetary(
        string="Total Amount",
        required=True,
        currency_field="currency_id",
        help="Total invoice amount including taxes",
    )

    paid_amount = fields.Monetary(
        string="Paid Amount",
        currency_field="currency_id",
        default=0.0,
        help="Amount already paid",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        help="Invoice currency",
    )

    # Partner info
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        help="Linked Odoo partner",
    )

    partner_name = fields.Char(
        string="Partner Name",
        help="Partner name from Tesote",
    )

    partner_vat = fields.Char(
        string="Partner VAT",
        help="Partner VAT/Tax ID from Tesote",
    )

    # Status
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("paid", "Paid"),
            ("partial", "Partially Paid"),
            ("overdue", "Overdue"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        help="Invoice status",
    )

    payment_status = fields.Selection(
        [
            ("not_paid", "Not Paid"),
            ("partial", "Partially Paid"),
            ("paid", "Fully Paid"),
        ],
        string="Payment Status",
        compute="_compute_payment_status",
        store=True,
        help="Computed payment status based on amounts",
    )

    amount_due = fields.Monetary(
        string="Amount Due",
        compute="_compute_amount_due",
        currency_field="currency_id",
        store=True,
        help="Remaining amount to be paid",
    )

    # Line items
    line_ids = fields.One2many(
        "tesote.invoice.line",
        "invoice_id",
        string="Invoice Lines",
        help="Invoice line items",
    )

    # Odoo integration
    account_move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        help="Related Odoo accounting entry",
    )

    is_reconciled = fields.Boolean(
        string="Reconciled",
        default=False,
        help="Whether invoice has been reconciled in Odoo",
    )

    # Metadata
    description = fields.Text(
        string="Description",
        help="Invoice description or notes",
    )

    invoice_data = fields.Text(
        string="Invoice Data",
        help="Additional invoice data in JSON format",
    )

    tesote_created_at = fields.Datetime(
        string="Created at Tesote",
        readonly=True,
        help="Creation date in Tesote system",
    )

    tesote_updated_at = fields.Datetime(
        string="Updated at Tesote",
        readonly=True,
        help="Last update date in Tesote system",
    )

    _sql_constraints = [
        (
            "tesote_id_account_uniq",
            "UNIQUE(tesote_id, account_id)",
            "Tesote invoice ID must be unique per account!",
        ),
    ]

    @api.depends("total_amount", "paid_amount")
    def _compute_payment_status(self):
        """Compute payment status based on paid and total amounts."""
        for invoice in self:
            if not invoice.total_amount:
                invoice.payment_status = "not_paid"
            elif invoice.paid_amount >= invoice.total_amount:
                invoice.payment_status = "paid"
            elif invoice.paid_amount > 0:
                invoice.payment_status = "partial"
            else:
                invoice.payment_status = "not_paid"

    @api.depends("total_amount", "paid_amount")
    def _compute_amount_due(self):
        """Compute remaining amount due."""
        for invoice in self:
            invoice.amount_due = (invoice.total_amount or 0.0) - (invoice.paid_amount or 0.0)

    def create_journal_entry(self):
        """
        Create journal entry from invoice.

        Returns:
            Created account.move record
        """
        self.ensure_one()

        if self.account_move_id:
            raise UserError(_("Journal entry already exists for this invoice"))

        return self._create_journal_entry()

    def _create_journal_entry(self):
        """
        Internal method to create journal entry.

        Creates an account.move of the appropriate type based on invoice_type.

        Returns:
            Created account.move record
        """
        self.ensure_one()

        # Determine move type based on invoice type
        move_type_map = {
            "customer_invoice": "out_invoice",
            "vendor_bill": "in_invoice",
            "credit_note": "out_refund",
            "debit_note": "in_refund",
        }
        move_type = move_type_map.get(self.invoice_type, "out_invoice")

        # Get or create partner
        partner = self._get_or_create_partner()

        # Get journal
        journal = self._get_invoice_journal()

        # Prepare move values
        move_vals = {
            "move_type": move_type,
            "journal_id": journal.id,
            "partner_id": partner.id if partner else False,
            "invoice_date": self.invoice_date,
            "invoice_date_due": self.due_date or self.invoice_date,
            "ref": f"TESOTE-INV-{self.tesote_id}",
            "narration": self.description,
            "currency_id": self.currency_id.id,
        }

        # Create invoice lines
        move_lines = []
        for line in self.line_ids:
            line_vals = {
                "name": line.description,
                "quantity": line.quantity,
                "price_unit": line.unit_price,
                "account_id": line.account_id.id if line.account_id else False,
                "product_id": line.product_id.id if line.product_id else False,
            }
            move_lines.append((0, 0, line_vals))

        # If no lines, create a single line with the total
        if not move_lines:
            income_account = self._get_default_income_account()
            move_lines.append(
                (
                    0,
                    0,
                    {
                        "name": self.invoice_number or self.description or "Invoice",
                        "quantity": 1,
                        "price_unit": self.total_amount,
                        "account_id": income_account.id if income_account else False,
                    },
                )
            )

        move_vals["invoice_line_ids"] = move_lines

        # Create and optionally post the move
        move = self.env["account.move"].create(move_vals)

        # Link to invoice
        self.account_move_id = move
        self.is_reconciled = True

        return move

    def _get_or_create_partner(self):
        """
        Get existing partner or create new one from invoice data.

        Returns:
            res.partner record or False
        """
        self.ensure_one()

        # If already linked, return existing
        if self.partner_id:
            return self.partner_id

        if not self.partner_name:
            return False

        # Try to find by VAT first
        partner = False
        if self.partner_vat:
            partner = self.env["res.partner"].search(
                [
                    ("vat", "=", self.partner_vat),
                    "|",
                    ("company_id", "=", self.backend_id.company_id.id),
                    ("company_id", "=", False),
                ],
                limit=1,
            )

        # Try to find by name
        if not partner:
            partner = self.env["res.partner"].search(
                [
                    ("name", "=ilike", self.partner_name),
                    "|",
                    ("company_id", "=", self.backend_id.company_id.id),
                    ("company_id", "=", False),
                ],
                limit=1,
            )

        # Create if not found
        if not partner:
            is_customer = self.invoice_type in ("customer_invoice", "credit_note")
            partner = self.env["res.partner"].create(
                {
                    "name": self.partner_name,
                    "vat": self.partner_vat or False,
                    "customer_rank": 1 if is_customer else 0,
                    "supplier_rank": 0 if is_customer else 1,
                    "company_id": self.backend_id.company_id.id,
                }
            )

        # Link partner to invoice
        self.partner_id = partner
        return partner

    def _get_invoice_journal(self):
        """
        Get appropriate journal for invoice type.

        Returns:
            account.journal record
        """
        self.ensure_one()

        # Determine journal type
        if self.invoice_type in ("customer_invoice", "credit_note"):
            journal_type = "sale"
            code = "TSINV"
            name = _("Tesote Sales")
        else:
            journal_type = "purchase"
            code = "TSBILL"
            name = _("Tesote Purchases")

        # Search for existing journal
        journal = self.env["account.journal"].search(
            [
                ("type", "=", journal_type),
                ("company_id", "=", self.backend_id.company_id.id),
                ("code", "=", code),
            ],
            limit=1,
        )

        # Create if not found
        if not journal:
            journal = self.env["account.journal"].create(
                {
                    "name": name,
                    "code": code,
                    "type": journal_type,
                    "company_id": self.backend_id.company_id.id,
                }
            )

        return journal

    def _get_default_income_account(self):
        """
        Get default income/expense account based on invoice type.

        Returns:
            account.account record
        """
        self.ensure_one()

        if self.invoice_type in ("customer_invoice", "credit_note"):
            # Income account
            account = self.env["account.account"].search(
                [
                    ("account_type", "=", "income"),
                    ("company_id", "=", self.backend_id.company_id.id),
                ],
                limit=1,
            )
        else:
            # Expense account
            account = self.env["account.account"].search(
                [
                    ("account_type", "=", "expense"),
                    ("company_id", "=", self.backend_id.company_id.id),
                ],
                limit=1,
            )

        return account

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
                # Parse to date only
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
        Create invoice from v2 sync API data.

        Args:
            account: tesote.account record
            data: Dictionary with invoice data from sync endpoint

        Returns:
            Created tesote.invoice record
        """
        # Get currency
        currency = account.currency_id
        if not currency:
            currency_code = data.get("currency") or data.get("iso_currency_code", "USD")
            currency = self.env["res.currency"].search([("name", "=", currency_code)], limit=1)
            if not currency:
                currency = self.env.company.currency_id

        # Map invoice type
        type_map = {
            "customer_invoice": "customer_invoice",
            "vendor_bill": "vendor_bill",
            "credit_note": "credit_note",
            "debit_note": "debit_note",
            # Also handle lowercase/alternative names from API
            "invoice": "customer_invoice",
            "bill": "vendor_bill",
            "refund": "credit_note",
        }
        invoice_type = type_map.get(data.get("type", "customer_invoice"), "customer_invoice")

        vals = {
            "account_id": account.id,
            "backend_id": account.backend_id.id,
            "tesote_id": data["invoice_id"],
            "invoice_number": data.get("invoice_number", data["invoice_id"]),
            "invoice_type": invoice_type,
            "invoice_date": self._parse_date(data.get("invoice_date")),
            "due_date": self._parse_date(data.get("due_date")),
            "subtotal": data.get("subtotal", 0.0),
            "tax_amount": data.get("tax_amount", 0.0),
            "total_amount": data.get("total_amount", 0.0),
            "paid_amount": data.get("paid_amount", 0.0),
            "currency_id": currency.id,
            "partner_name": data.get("partner_name"),
            "partner_vat": data.get("partner_vat"),
            "status": data.get("status", "draft"),
            "description": data.get("description"),
            "invoice_data": str(data),
            "tesote_created_at": self._parse_datetime(data.get("created_at")),
            "tesote_updated_at": self._parse_datetime(data.get("updated_at")),
        }

        invoice = self.create(vals)

        # Create invoice lines if provided
        lines_data = data.get("lines", [])
        for line_data in lines_data:
            self.env["tesote.invoice.line"].create_from_sync_data(invoice, line_data)

        return invoice

    def update_from_sync_data(self, data):
        """
        Update invoice from v2 sync API data.

        Args:
            data: Dictionary with invoice data from sync endpoint
        """
        self.ensure_one()

        # Map invoice type
        type_map = {
            "customer_invoice": "customer_invoice",
            "vendor_bill": "vendor_bill",
            "credit_note": "credit_note",
            "debit_note": "debit_note",
            "invoice": "customer_invoice",
            "bill": "vendor_bill",
            "refund": "credit_note",
        }

        vals = {
            "invoice_number": data.get("invoice_number", self.invoice_number),
            "invoice_type": type_map.get(data.get("type"), self.invoice_type),
            "invoice_date": self._parse_date(data.get("invoice_date")) or self.invoice_date,
            "due_date": self._parse_date(data.get("due_date")),
            "subtotal": data.get("subtotal", self.subtotal),
            "tax_amount": data.get("tax_amount", self.tax_amount),
            "total_amount": data.get("total_amount", self.total_amount),
            "paid_amount": data.get("paid_amount", self.paid_amount),
            "partner_name": data.get("partner_name", self.partner_name),
            "partner_vat": data.get("partner_vat", self.partner_vat),
            "status": data.get("status", self.status),
            "description": data.get("description", self.description),
            "invoice_data": str(data),
            "tesote_updated_at": self._parse_datetime(data.get("updated_at")),
        }

        self.write(vals)

        # Update invoice lines if provided
        lines_data = data.get("lines")
        if lines_data is not None:
            # Remove existing lines and recreate
            self.line_ids.unlink()
            for line_data in lines_data:
                self.env["tesote.invoice.line"].create_from_sync_data(self, line_data)

    def action_create_journal_entry(self):
        """Button action to create journal entry."""
        self.ensure_one()
        move = self.create_journal_entry()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_journal_entry(self):
        """Button action to view linked journal entry."""
        self.ensure_one()
        if not self.account_move_id:
            raise UserError(_("No journal entry linked to this invoice"))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.account_move_id.id,
            "view_mode": "form",
            "target": "current",
        }
