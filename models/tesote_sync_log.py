# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Sync Log Model.
Tracks all synchronization events and operations.
"""

from datetime import timedelta

from odoo import api, fields, models

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="sync")


class TesoteSyncLog(models.Model):
    """Log entries for Tesote synchronization operations."""

    _name = "tesote.sync.log"
    _description = "Tesote Sync Log"
    _order = "create_date desc"
    _rec_name = "operation"

    backend_id = fields.Many2one(
        "tesote.backend", string="Backend", required=True, ondelete="cascade"
    )

    operation = fields.Selection(
        [
            ("test_connection", "Test Connection"),
            ("import_accounts", "Import Accounts"),
            ("sync_transactions", "Sync Transactions"),
            ("sync_single_account", "Sync Single Account"),
            ("webhook", "Webhook Event"),
            ("manual_sync", "Manual Sync"),
            ("scheduled_sync", "Scheduled Sync"),
        ],
        string="Operation",
        required=True,
    )

    status = fields.Selection(
        [
            ("started", "Started"),
            ("in_progress", "In Progress"),
            ("success", "Success"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        string="Status",
        required=True,
        default="started",
    )

    start_date = fields.Datetime(string="Start Time", default=fields.Datetime.now, required=True)

    end_date = fields.Datetime(string="End Time")

    duration = fields.Float(string="Duration (seconds)", compute="_compute_duration", store=True)

    account_id = fields.Many2one(
        "tesote.account",
        string="Account",
        help="Specific account if operation was account-specific",
    )

    records_added = fields.Integer(string="Records Added", default=0)

    records_modified = fields.Integer(string="Records Modified", default=0)

    records_removed = fields.Integer(string="Records Removed", default=0)

    error_message = fields.Text(string="Error Message")

    details = fields.Text(string="Details", help="Additional information about the sync operation")

    api_calls = fields.Integer(string="API Calls Made", default=0)

    user_id = fields.Many2one("res.users", string="User", default=lambda self: self.env.user)

    is_background = fields.Boolean(string="Background Job", default=False)

    cursor_before = fields.Char(string="Cursor Before", help="Sync cursor value before operation")

    cursor_after = fields.Char(string="Cursor After", help="Sync cursor value after operation")

    @api.depends("start_date", "end_date")
    def _compute_duration(self):
        """Compute duration in seconds."""
        for log in self:
            if log.start_date and log.end_date:
                delta = log.end_date - log.start_date
                log.duration = delta.total_seconds()
            else:
                log.duration = 0

    @api.model
    def create_log(self, backend, operation, **kwargs):
        """
        Create a new sync log entry.

        Args:
            backend: tesote.backend record
            operation: Operation type string
            **kwargs: Additional fields for the log

        Returns:
            Created log record
        """
        vals = {
            "backend_id": backend.id,
            "operation": operation,
            "status": "started",
            "start_date": fields.Datetime.now(),
        }
        vals.update(kwargs)
        return self.create(vals)

    def set_success(self, **kwargs):
        """Mark log as successful."""
        self.ensure_one()
        vals = {
            "status": "success",
            "end_date": fields.Datetime.now(),
        }
        vals.update(kwargs)
        self.write(vals)
        return self

    def set_error(self, error_message, **kwargs):
        """Mark log as failed with error."""
        self.ensure_one()
        vals = {
            "status": "error",
            "end_date": fields.Datetime.now(),
            "error_message": str(error_message),
        }
        vals.update(kwargs)
        self.write(vals)
        return self

    def set_warning(self, message, **kwargs):
        """Mark log with warning."""
        self.ensure_one()
        vals = {
            "status": "warning",
            "end_date": fields.Datetime.now(),
            "details": message,
        }
        vals.update(kwargs)
        self.write(vals)
        return self

    def update_progress(self, **kwargs):
        """Update log with progress information."""
        self.ensure_one()
        vals = {"status": "in_progress"}
        vals.update(kwargs)
        self.write(vals)
        return self

    @api.model
    def cleanup_old_logs(self, days=30):
        """
        Remove old log entries.

        Args:
            days: Number of days to keep logs (default 30)
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_logs = self.search([("create_date", "<", cutoff_date)])
        old_logs.unlink()
        _logger.info(f"Cleaned up {len(old_logs)} old sync log entries")

    def name_get(self):
        """Custom display name for logs."""
        result = []
        for log in self:
            name = f"{log.operation} - {log.start_date}"
            if log.account_id:
                name += f" ({log.account_id.name})"
            result.append((log.id, name))
        return result
