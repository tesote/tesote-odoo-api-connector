# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Account Balance History Model.
Stores historical balance snapshots for trend analysis.
"""

from odoo import _, api, fields, models

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="sync")


class TesoteAccountBalanceHistory(models.Model):
    """Historical balance snapshots for Tesote accounts."""

    _name = "tesote.account.balance.history"
    _description = "Tesote Account Balance History"
    _order = "recorded_at desc"
    _rec_name = "display_name"

    # Core fields
    account_id = fields.Many2one(
        "tesote.account",
        string="Account",
        required=True,
        ondelete="cascade",
        index=True,
        help="The Tesote account this balance snapshot belongs to",
    )

    balance = fields.Float(
        string="Balance",
        digits="Account",
        required=True,
        help="Account balance at the time of recording",
    )

    previous_balance = fields.Float(
        string="Previous Balance",
        digits="Account",
        help="Balance before this snapshot",
    )

    balance_change = fields.Float(
        string="Balance Change",
        digits="Account",
        compute="_compute_balance_change",
        store=True,
        help="Difference between current and previous balance",
    )

    balance_change_percent = fields.Float(
        string="Change (%)",
        compute="_compute_balance_change",
        store=True,
        digits=(16, 2),
        help="Percentage change from previous balance",
    )

    recorded_at = fields.Datetime(
        string="Recorded At",
        required=True,
        default=fields.Datetime.now,
        index=True,
        help="When this balance snapshot was recorded",
    )

    source = fields.Selection(
        [
            ("sync", "Synchronization"),
            ("webhook", "Webhook Update"),
            ("manual", "Manual Refresh"),
        ],
        string="Source",
        required=True,
        default="sync",
        help="How this balance was recorded",
    )

    # Traceability
    sync_log_id = fields.Many2one(
        "tesote.sync.log",
        string="Sync Log",
        ondelete="set null",
        help="Associated sync log entry for traceability",
    )

    # Related fields for reporting
    currency_id = fields.Many2one(
        related="account_id.currency_id",
        string="Currency",
        store=True,
        readonly=True,
    )

    bank_name = fields.Char(
        related="account_id.bank_name",
        string="Bank",
        store=True,
        readonly=True,
    )

    account_name = fields.Char(
        related="account_id.name",
        string="Account Name",
        store=True,
        readonly=True,
    )

    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
    )

    # Date field for grouping in graph views
    recorded_date = fields.Date(
        string="Date",
        compute="_compute_recorded_date",
        store=True,
        help="Date portion of recorded_at for grouping",
    )

    @api.depends("balance", "previous_balance")
    def _compute_balance_change(self):
        """Compute the balance change and percentage."""
        for record in self:
            record.balance_change = record.balance - (record.previous_balance or 0)
            if record.previous_balance:
                record.balance_change_percent = (
                    (record.balance_change / abs(record.previous_balance)) * 100
                )
            else:
                record.balance_change_percent = 0.0

    @api.depends("account_id", "recorded_at")
    def _compute_display_name(self):
        """Compute display name for the record."""
        for record in self:
            if record.account_id and record.recorded_at:
                record.display_name = f"{record.account_id.name} - {record.recorded_at}"
            else:
                record.display_name = _("New Balance Record")

    @api.depends("recorded_at")
    def _compute_recorded_date(self):
        """Extract date from recorded_at for graph grouping."""
        for record in self:
            if record.recorded_at:
                record.recorded_date = record.recorded_at.date()
            else:
                record.recorded_date = False

    @api.model
    def record_balance(self, account, balance, source="sync", sync_log=None):
        """
        Record a balance snapshot for an account.

        Args:
            account: tesote.account record
            balance: Current balance value
            source: How the balance was obtained (sync/webhook/manual)
            sync_log: Optional tesote.sync.log record for traceability

        Returns:
            Created balance history record
        """
        # Get the previous balance from the most recent history record
        last_record = self.search(
            [("account_id", "=", account.id)],
            order="recorded_at desc",
            limit=1,
        )

        previous_balance = last_record.balance if last_record else 0.0

        # Skip if balance hasn't changed significantly
        if abs(balance - previous_balance) < 0.01:
            _logger.debug(
                f"Skipping balance history for {account.name}: "
                f"no significant change ({previous_balance} -> {balance})"
            )
            return False

        vals = {
            "account_id": account.id,
            "balance": balance,
            "previous_balance": previous_balance,
            "source": source,
            "recorded_at": fields.Datetime.now(),
        }

        if sync_log:
            vals["sync_log_id"] = sync_log.id

        record = self.create(vals)
        _logger.debug(
            f"Recorded balance history for {account.name}: "
            f"{previous_balance} -> {balance} (change: {balance - previous_balance})"
        )
        return record

    @api.model
    def cleanup_old_records(self, days=365):
        """
        Remove old balance history records beyond retention period.

        Args:
            days: Number of days to retain records (default 365)
        """
        from datetime import timedelta

        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_records = self.search([("recorded_at", "<", cutoff_date)])
        count = len(old_records)
        old_records.unlink()
        _logger.info(f"Cleaned up {count} old balance history records")
        return count
