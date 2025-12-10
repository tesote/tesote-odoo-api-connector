# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Invoice Line Model.
Represents invoice line items synchronized from Tesote API.
"""

from odoo import api, fields, models

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="sync")


class TesoteInvoiceLine(models.Model):
    """Invoice line item from Tesote API."""

    _name = "tesote.invoice.line"
    _description = "Tesote Invoice Line"
    _order = "sequence, id"

    invoice_id = fields.Many2one(
        "tesote.invoice",
        string="Invoice",
        required=True,
        ondelete="cascade",
        help="Parent invoice",
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Sequence for ordering lines",
    )

    # Line details
    description = fields.Char(
        string="Description",
        required=True,
        help="Line item description",
    )

    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        digits="Product Unit of Measure",
        help="Quantity of items",
    )

    unit_price = fields.Monetary(
        string="Unit Price",
        currency_field="currency_id",
        help="Price per unit",
    )

    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        default=0.0,
        help="Discount percentage",
    )

    tax_amount = fields.Monetary(
        string="Tax Amount",
        currency_field="currency_id",
        help="Tax amount for this line",
    )

    subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_subtotal",
        currency_field="currency_id",
        store=True,
        help="Line subtotal before tax",
    )

    total_amount = fields.Monetary(
        string="Total",
        currency_field="currency_id",
        help="Line total including tax",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="invoice_id.currency_id",
        store=True,
        readonly=True,
    )

    # Product mapping (optional)
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        help="Linked Odoo product",
    )

    # Account mapping (optional)
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        help="Accounting account for this line",
    )

    # Metadata
    tesote_line_id = fields.Char(
        string="Tesote Line ID",
        help="External line identifier from Tesote",
    )

    line_data = fields.Text(
        string="Line Data",
        help="Additional line data in JSON format",
    )

    @api.depends("quantity", "unit_price", "discount")
    def _compute_subtotal(self):
        """Compute line subtotal before tax."""
        for line in self:
            price = line.unit_price * (1 - (line.discount or 0.0) / 100.0)
            line.subtotal = line.quantity * price

    @api.model
    def create_from_sync_data(self, invoice, data):
        """
        Create invoice line from sync API data.

        Args:
            invoice: tesote.invoice record
            data: Dictionary with line data from sync endpoint

        Returns:
            Created tesote.invoice.line record
        """
        vals = {
            "invoice_id": invoice.id,
            "description": data.get("description", "Line item"),
            "quantity": data.get("quantity", 1.0),
            "unit_price": data.get("unit_price", 0.0),
            "discount": data.get("discount", 0.0),
            "tax_amount": data.get("tax_amount", 0.0),
            "total_amount": data.get("total_amount", 0.0),
            "tesote_line_id": data.get("line_id"),
            "line_data": str(data),
        }

        # Set sequence if provided
        if "sequence" in data:
            vals["sequence"] = data["sequence"]

        return self.create(vals)

    def update_from_sync_data(self, data):
        """
        Update invoice line from sync API data.

        Args:
            data: Dictionary with line data from sync endpoint
        """
        self.ensure_one()

        vals = {
            "description": data.get("description", self.description),
            "quantity": data.get("quantity", self.quantity),
            "unit_price": data.get("unit_price", self.unit_price),
            "discount": data.get("discount", self.discount),
            "tax_amount": data.get("tax_amount", self.tax_amount),
            "total_amount": data.get("total_amount", self.total_amount),
            "line_data": str(data),
        }

        if "sequence" in data:
            vals["sequence"] = data["sequence"]

        self.write(vals)
