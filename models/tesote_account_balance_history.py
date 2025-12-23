# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Account Balance History Model.
Tracks balance snapshots for historical tracking and dashboard visualization.
"""

from odoo import api, fields, models


class TesoteAccountBalanceHistory(models.Model):
    """Historical balance snapshots for Tesote accounts."""

    _name = "tesote.account.balance.history"
    _description = "Tesote Account Balance History"
    _order = "recorded_at desc"
    _rec_name = "display_name"

    account_id = fields.Many2one(
        "tesote.account",
        string="Account",
        required=True,
        ondelete="cascade",
        index=True,
    )

    balance = fields.Float(
        string="Balance",
        digits="Account",
        help="Balance at time of recording",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        help="Currency of the balance",
    )

    recorded_at = fields.Datetime(
        string="Recorded At",
        default=fields.Datetime.now,
        required=True,
        index=True,
    )

    previous_balance = fields.Float(
        string="Previous Balance",
        digits="Account",
        help="Previous recorded balance",
    )

    balance_change = fields.Float(
        string="Balance Change",
        digits="Account",
        compute="_compute_balance_change",
        store=True,
        help="Difference from previous balance",
    )

    balance_change_percent = fields.Float(
        string="Change %",
        compute="_compute_balance_change",
        store=True,
        help="Percentage change from previous balance",
    )

    sync_log_id = fields.Many2one(
        "tesote.sync.log",
        string="Sync Log",
        help="Related sync operation that triggered this snapshot",
    )

    source = fields.Selection(
        [
            ("sync", "API Sync"),
            ("webhook", "Webhook Update"),
            ("manual", "Manual Update"),
        ],
        string="Source",
        default="sync",
        help="How this snapshot was captured",
    )

    # Related fields for efficient reporting
    backend_id = fields.Many2one(
        related="account_id.backend_id",
        store=True,
        string="Backend",
    )

    account_name = fields.Char(
        related="account_id.name",
        store=True,
        string="Account Name",
    )

    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )

    @api.depends("balance", "previous_balance")
    def _compute_balance_change(self):
        """Compute balance change amount and percentage."""
        for record in self:
            record.balance_change = record.balance - record.previous_balance
            if record.previous_balance:
                record.balance_change_percent = (
                    record.balance_change / abs(record.previous_balance)
                ) * 100
            else:
                record.balance_change_percent = 0.0

    @api.depends("account_id", "recorded_at", "balance")
    def _compute_display_name(self):
        """Compute display name for the record."""
        for record in self:
            if record.account_id and record.recorded_at:
                date_str = fields.Datetime.to_string(record.recorded_at)[:10]
                record.display_name = f"{record.account_id.name} - {date_str}"
            else:
                record.display_name = f"Balance: {record.balance}"
