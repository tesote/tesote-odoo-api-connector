# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Backend Model.
Manages connection configuration and authentication to Tesote API.
"""

import threading

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="sync")


class TesoteBackend(models.Model):
    """Backend configuration for Tesote API connection."""

    _name = "tesote.backend"
    _description = "Tesote Backend Configuration"
    _rec_name = "name"

    @api.model
    def _default_name(self):
        """Default name for singleton."""
        return "Tesote API Configuration"

    name = fields.Char(
        string="Name", required=True, default=_default_name, help="Backend instance name"
    )

    api_url = fields.Char(
        string="API URL",
        required=True,
        default="https://staging.tesote.com",
        help="Tesote API base URL",
    )

    api_version = fields.Char(
        string="API Version", required=True, default="v2", help="API version to use (v2.0.0)"
    )

    api_token = fields.Char(
        string="API Token", required=True, help="Bearer token for authentication"
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("active", "Active"),
        ],
        string="State",
        default="draft",
        required=True,
    )

    rate_limit_tier = fields.Selection(
        [
            ("standard", "Standard (200/min)"),
            ("premium", "Premium (500/min)"),
            ("enterprise", "Enterprise (1000/min)"),
        ],
        string="Rate Limit Tier",
        default="standard",
        required=True,
    )

    rate_limit_calls = fields.Integer(
        string="Rate Limit Calls", default=200, required=True, help="Maximum API calls allowed"
    )

    rate_limit_period = fields.Integer(
        string="Rate Limit Period (seconds)",
        default=60,
        required=True,
        help="Rate limit time window in seconds",
    )

    active = fields.Boolean(string="Active", default=True)

    company_id = fields.Many2one(
        "res.company", string="Company", required=True, default=lambda self: self.env.company
    )

    account_ids = fields.One2many("tesote.account", "backend_id", string="Accounts")

    last_sync_date = fields.Datetime(string="Last Synchronization", readonly=True)

    webhook_url = fields.Char(
        string="Webhook URL", help="URL to receive Tesote webhook notifications"
    )

    webhook_secret = fields.Char(
        string="Webhook Secret", help="HMAC secret for webhook signature verification"
    )

    # Default values as class attribute for testing
    _defaults = {
        "api_version": "v2",
        "api_url": "https://staging.tesote.com",
        "rate_limit_calls": 200,  # v2 standard tier
        "rate_limit_period": 60,
        "active": True,
    }

    @api.model
    def _get_default_api_url(self):
        """Get default API URL."""
        return self._defaults["api_url"]

    # Computed fields
    account_count = fields.Integer(string="Account Count", compute="_compute_counts", store=False)

    transaction_count = fields.Integer(
        string="Transaction Count", compute="_compute_counts", store=False
    )

    sync_state = fields.Char(string="Sync State", compute="_compute_sync_state", store=False)

    last_sync_date = fields.Datetime(
        string="Last Sync Date", compute="_compute_last_sync_date", store=False
    )

    last_account_import_date = fields.Datetime(string="Last Account Import")

    last_transaction_sync_date = fields.Datetime(string="Last Transaction Sync")

    auto_sync_enabled = fields.Boolean(string="Auto Sync Enabled", default=False)

    sync_interval_hours = fields.Integer(string="Sync Interval (hours)", default=24)

    sync_log_ids = fields.One2many("tesote.sync.log", "backend_id", string="Sync Logs")

    sync_log_count = fields.Integer(
        string="Sync Log Count", compute="_compute_sync_log_count", store=False
    )

    @property
    def _module_version(self):
        """Get module version from manifest."""
        try:
            # Try to get version from installed module
            module = (
                self.env["ir.module.module"]
                .sudo()
                .search([("name", "=", "tesote_odoo_api_connector")], limit=1)
            )
            if module and module.latest_version:
                return module.latest_version
        except Exception:
            pass
        # Fallback to hardcoded version
        return "18.0.1.0.0"

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure only one backend exists (batch-compatible)."""
        existing = self.search([("id", "!=", 0)], limit=1)
        if existing:
            raise UserError(
                _(
                    "Only one Tesote Backend configuration is allowed. Please edit the existing configuration."
                )
            )
        return super(TesoteBackend, self).create(vals_list)

    @api.constrains("active")
    def _check_single_backend(self):
        """Ensure only one backend configuration exists."""
        if self.search_count([("id", "!=", 0)]) > 1:
            raise UserError(_("Only one Tesote Backend configuration is allowed."))

    def write(self, vals):
        """Override write to handle auto sync settings."""
        result = super(TesoteBackend, self).write(vals)

        # Update cron job when auto sync settings change
        if "auto_sync_enabled" in vals or "sync_interval_hours" in vals:
            self._update_cron_job()

        return result

    def _update_cron_job(self):
        """Update the cron job based on auto sync settings."""
        cron_sync = self.env.ref(
            "tesote_connector.ir_cron_tesote_sync_transactions", raise_if_not_found=False
        )

        if cron_sync:
            if self.auto_sync_enabled and self.active:
                # Enable cron and set interval
                cron_sync.active = True
                cron_sync.interval_number = self.sync_interval_hours or 24
                cron_sync.interval_type = "hours"
                _logger.info(f"Enabled auto sync every {self.sync_interval_hours} hours")
            else:
                # Disable cron
                cron_sync.active = False
                _logger.info("Disabled auto sync")

    @api.model
    def action_open_configuration(self):
        """Open the singleton configuration or create if it doesn't exist."""
        backend = self.search([], limit=1)
        if not backend:
            # Create default configuration
            backend = self.create(
                {
                    "name": "Tesote API Configuration",
                    "api_url": "https://equipo.tesote.com",
                    "api_version": "v2",
                    "api_token": "",  # User needs to set this
                    "state": "draft",
                    "rate_limit_tier": "standard",
                    "rate_limit_calls": 200,
                    "rate_limit_period": 60,
                }
            )

        # Return action to open the form view
        return {
            "type": "ir.actions.act_window",
            "name": _("Tesote Configuration"),
            "res_model": "tesote.backend",
            "res_id": backend.id,
            "view_mode": "form",
            "view_id": self.env.ref("tesote_connector.view_tesote_backend_form").id,
            "target": "current",
        }

    @api.depends("account_ids")
    def _compute_counts(self):
        """Compute account and transaction counts."""
        for backend in self:
            backend.account_count = len(backend.account_ids)
            backend.transaction_count = self.env["tesote.transaction"].search_count(
                [("backend_id", "=", backend.id)]
            )

    def _compute_sync_state(self):
        """Compute sync state."""
        for backend in self:
            if backend.state == "active":
                backend.sync_state = "Ready"
            else:
                backend.sync_state = "Not configured"

    def _compute_last_sync_date(self):
        """Compute last sync date."""
        for backend in self:
            dates = [
                d
                for d in [backend.last_account_import_date, backend.last_transaction_sync_date]
                if d
            ]
            backend.last_sync_date = max(dates) if dates else False

    @api.depends("sync_log_ids")
    def _compute_sync_log_count(self):
        """Compute sync log count."""
        for backend in self:
            backend.sync_log_count = len(backend.sync_log_ids)

    def test_connection(self):
        """
        Test connection to Tesote API.

        Returns:
            Notification action if successful

        Raises:
            UserError: If connection fails
        """
        self.ensure_one()

        # Create sync log
        SyncLog = self.env["tesote.sync.log"]
        log = SyncLog.create_log(self, "test_connection")

        try:
            from ..components.adapter import TesoteAdapter

            # Create adapter instance
            adapter = TesoteAdapter(self)

            # Test API status
            result = adapter.get_status()

            if result.get("status") == "ok":
                # Also test whoami to verify token
                client_info = adapter.get_whoami()

                _logger.info(f"Whoami response: {client_info}")

                # Try different possible field names from the API
                client_name = (
                    client_info.get("name")
                    or client_info.get("client_name")
                    or client_info.get("workspace_name")
                    or client_info.get("client", {}).get("name")
                    or client_info.get("workspace", {}).get("name")
                    or "Connected"
                )

                environment = (
                    client_info.get("environment")
                    or client_info.get("env")
                    or client_info.get("stage")
                    or "Production"
                )

                message = _("Connection successful!\nClient: %s\nEnvironment: %s") % (
                    client_name,
                    environment,
                )

                # Update state to confirmed if in draft
                if self.state == "draft":
                    self.state = "confirmed"

                # Mark log as successful
                log.set_success(
                    api_calls=2,  # status + whoami
                    details=f"Connected to {client_name} - {environment}",
                )

                # Show success notification
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Success"),
                        "message": message,
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                raise UserError(_("API is not available"))

        except Exception as e:
            _logger.error(f"Connection test failed: {str(e)}")
            log.set_error(str(e))
            raise UserError(_("Connection failed: %s") % str(e))

    def action_view_accounts(self):
        """Open accounts view."""
        self.ensure_one()
        return {
            "name": _("Tesote Accounts"),
            "type": "ir.actions.act_window",
            "res_model": "tesote.account",
            "view_mode": "list,form",
            "domain": [("backend_id", "=", self.id)],
            "context": {"default_backend_id": self.id},
        }

    def action_view_transactions(self):
        """Open transactions view."""
        self.ensure_one()
        return {
            "name": _("Tesote Transactions"),
            "type": "ir.actions.act_window",
            "res_model": "tesote.transaction",
            "view_mode": "list,form,pivot,graph",
            "domain": [("backend_id", "=", self.id)],
            "context": {"default_backend_id": self.id},
        }

    def action_view_sync_logs(self):
        """Open sync logs view."""
        self.ensure_one()
        return {
            "name": _("Sync Logs"),
            "type": "ir.actions.act_window",
            "res_model": "tesote.sync.log",
            "view_mode": "list,form",
            "domain": [("backend_id", "=", self.id)],
            "context": {"default_backend_id": self.id},
        }

    def import_accounts(self):
        """Import accounts from Tesote - runs in background."""
        self.ensure_one()

        # Start background import
        threading.Thread(
            target=self._import_accounts_background, args=(self.id,), daemon=True
        ).start()

        # Return immediate notification
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import Started"),
                "message": _(
                    "Account import has been started in the background. Check the sync logs for progress."
                ),
                "type": "info",
                "sticky": False,
            },
        }

    def _import_accounts_background(self, backend_id):
        """Background worker for account import."""
        with self.env.registry.cursor() as new_cr:
            # Create new environment with new cursor
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            backend = new_env["tesote.backend"].browse(backend_id)

            # Create sync log
            SyncLog = new_env["tesote.sync.log"]
            log = SyncLog.create_log(
                backend,
                "import_accounts",
                is_background=True,
                details="Background import of all accounts",
            )

            try:
                try:
                    from ..components.adapter import TesoteAdapter
                    from ..components.importer import TesoteAccountBatchImporter
                except ImportError:
                    from components.adapter import TesoteAdapter
                    from components.importer import TesoteAccountBatchImporter

                # Create adapter and importer
                adapter = TesoteAdapter(backend)
                importer = TesoteAccountBatchImporter(new_env, backend.id)

                # Update log progress
                log.update_progress(details="Starting account import from Tesote API", api_calls=0)

                # Import accounts
                count = importer.run(adapter)

                # Update last import date
                backend.last_account_import_date = fields.Datetime.now()

                # Mark log as successful
                log.set_success(
                    records_added=count,
                    api_calls=1,
                    details=f"Background import completed: {count} accounts imported",
                )

                _logger.info(f"Background account import completed: {count} accounts imported")

                # Commit the transaction
                new_cr.commit()

            except Exception as e:
                _logger.error(f"Background account import failed: {str(e)}")
                log.set_error(str(e))
                # Rollback in case of error
                new_cr.rollback()

    def sync_all_transactions(self):
        """Sync transactions for all accounts - runs in background."""
        self.ensure_one()

        if not self.account_ids:
            raise UserError(_("No accounts to sync. Please import accounts first."))

        # Start background sync
        threading.Thread(
            target=self._sync_transactions_background, args=(self.id,), daemon=True
        ).start()

        # Return immediate notification
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sync Started"),
                "message": _(
                    "Transaction sync has been started in the background. Check the sync logs for progress."
                ),
                "type": "info",
                "sticky": False,
            },
        }

    def _sync_transactions_background(self, backend_id):
        """Background worker for transaction sync."""
        with self.env.registry.cursor() as new_cr:
            # Create new environment with new cursor
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            backend = new_env["tesote.backend"].browse(backend_id)

            # Create sync log
            SyncLog = new_env["tesote.sync.log"]
            log = SyncLog.create_log(
                backend,
                "sync_transactions",
                is_background=True,
                details="Background sync of all accounts",
            )

            try:
                # Perform the actual sync
                total_added = 0
                total_modified = 0
                total_removed = 0
                api_calls = 0

                from ..components.adapter import TesoteAdapter

                adapter = TesoteAdapter(backend)

                for account in backend.account_ids:
                    # Update log progress
                    log.update_progress(
                        details=f"Syncing account {account.name}", api_calls=api_calls
                    )

                    cursor_before = account.sync_cursor

                    try:
                        # Sync this account
                        sync_result = adapter.sync_transactions(
                            tesote_account_id=account.tesote_id,
                            cursor=account.sync_cursor,
                            count=100,
                        )
                        api_calls += 1

                        # Process results
                        added_count = len(sync_result.get("added", []))
                        modified_count = len(sync_result.get("modified", []))
                        removed_count = len(sync_result.get("removed", []))

                        total_added += added_count
                        total_modified += modified_count
                        total_removed += removed_count

                        # Process transactions
                        backend._process_sync_results(account, sync_result)

                        # Update cursor
                        if sync_result.get("next_cursor"):
                            account.sync_cursor = sync_result["next_cursor"]

                        _logger.info(
                            f"Synced account {account.name}: "
                            f"+{added_count} ~{modified_count} -{removed_count}"
                        )

                    except UserError as e:
                        if str(e) == "HISTORY_SYNC_FORBIDDEN:SKIP":
                            _logger.info(f"Historical sync forbidden for account {account.name}")
                            account.sync_cursor = "synced_without_history"
                        else:
                            raise

                # Update backend sync date
                backend.last_sync_date = fields.Datetime.now()
                backend.last_transaction_sync_date = fields.Datetime.now()

                # Mark log as successful
                log.set_success(
                    records_added=total_added,
                    records_modified=total_modified,
                    records_removed=total_removed,
                    api_calls=api_calls,
                    details=f"Successfully synced {len(backend.account_ids)} accounts",
                )

                new_cr.commit()
                _logger.info(
                    f"Background sync completed: +{total_added} ~{total_modified} -{total_removed}"
                )

            except Exception as e:
                new_cr.rollback()
                log.set_error(str(e), api_calls=api_calls)
                _logger.error(f"Background sync failed: {str(e)}")
                raise

    def _scheduled_full_sync_background(self, backend_id):
        """Background worker for scheduled full sync (accounts + transactions)."""
        with self.env.registry.cursor() as new_cr:
            # Create new environment with new cursor
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            backend = new_env["tesote.backend"].browse(backend_id)

            # Create sync log for the full operation
            SyncLog = new_env["tesote.sync.log"]
            log = SyncLog.create_log(
                backend,
                "scheduled_sync",
                is_background=True,
                details="Scheduled full sync: accounts + transactions",
            )

            try:
                total_accounts_imported = 0
                total_transactions_added = 0
                total_transactions_modified = 0
                total_transactions_removed = 0
                api_calls = 0

                # Step 1: Import accounts
                log.update_progress(details="Importing accounts...")

                from ..components.adapter import TesoteAdapter
                from ..components.importer import TesoteAccountBatchImporter

                adapter = TesoteAdapter(backend)
                importer = TesoteAccountBatchImporter(new_env, backend.id)

                accounts_count = importer.run(adapter)
                api_calls += 1
                total_accounts_imported = accounts_count

                backend.last_account_import_date = fields.Datetime.now()

                _logger.info(f"Scheduled sync: imported {accounts_count} accounts")

                # Step 2: Sync transactions for all accounts
                log.update_progress(
                    details="Syncing transactions for all accounts...",
                    records_added=total_accounts_imported,
                    api_calls=api_calls,
                )

                for account in backend.account_ids:
                    log.update_progress(
                        details=f"Syncing transactions for account {account.name}",
                        api_calls=api_calls,
                    )

                    try:
                        # Sync this account
                        sync_result = adapter.sync_transactions(
                            tesote_account_id=account.tesote_id,
                            cursor=account.sync_cursor,
                            count=100,
                        )
                        api_calls += 1

                        # Process results
                        added_count = len(sync_result.get("added", []))
                        modified_count = len(sync_result.get("modified", []))
                        removed_count = len(sync_result.get("removed", []))

                        total_transactions_added += added_count
                        total_transactions_modified += modified_count
                        total_transactions_removed += removed_count

                        # Process transactions
                        backend._process_sync_results(account, sync_result)

                        # Update cursor
                        if sync_result.get("next_cursor"):
                            account.sync_cursor = sync_result["next_cursor"]

                        _logger.info(
                            f"Scheduled sync - account {account.name}: "
                            f"+{added_count} ~{modified_count} -{removed_count}"
                        )

                    except Exception as account_error:
                        _logger.warning(
                            f"Scheduled sync failed for account {account.name}: {str(account_error)}"
                        )
                        # Continue with other accounts
                        continue

                # Update backend sync dates
                backend.last_sync_date = fields.Datetime.now()
                backend.last_transaction_sync_date = fields.Datetime.now()

                # Mark log as successful
                log.set_success(
                    records_added=total_accounts_imported + total_transactions_added,
                    records_modified=total_transactions_modified,
                    records_removed=total_transactions_removed,
                    api_calls=api_calls,
                    details=f"Scheduled sync completed: {total_accounts_imported} accounts, "
                    f"{total_transactions_added} transactions added, "
                    f"{total_transactions_modified} modified, "
                    f"{total_transactions_removed} removed",
                )

                new_cr.commit()
                _logger.info(
                    f"Scheduled full sync completed for {backend.name}: "
                    f"accounts={total_accounts_imported}, transactions: "
                    f"+{total_transactions_added} ~{total_transactions_modified} -{total_transactions_removed}"
                )

            except Exception as e:
                new_cr.rollback()
                log.set_error(str(e), api_calls=api_calls)
                _logger.error(f"Scheduled full sync failed for {backend.name}: {str(e)}")
                raise

    def import_all_accounts(self):
        """
        Import all accounts from Tesote API.

        This method fetches all accounts and creates/updates them.
        """
        self.ensure_one()

        # This method was for OCA Component framework
        # Simply call import_accounts instead
        return self.import_accounts()

        self.last_sync_date = fields.Datetime.now()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Accounts imported successfully"),
                "type": "success",
                "sticky": False,
            },
        }

    def sync_transactions_v2(self, account_ids=None):
        """
        Sync transactions using v2 Client to Tesote Sync endpoint.

        Uses cursor-based synchronization for efficient updates.

        Args:
            account_ids: List of tesote.account IDs to sync
        """
        self.ensure_one()

        if not account_ids:
            account_ids = self.account_ids.ids

        accounts = self.env["tesote.account"].browse(account_ids)
        total_added = 0
        total_modified = 0
        total_removed = 0

        from ..components.adapter import TesoteAdapter

        adapter = TesoteAdapter(self)

        for account in accounts:
            # Get stored cursor for this account
            # For initial sync, use "latest" to get most recent transactions only
            # (Historical sync may be forbidden by the API)
            cursor = account.sync_cursor

            _logger.info(
                f"=== PROCESSING ACCOUNT ===\n"
                f"Account Name: {account.name}\n"
                f"Account ID: {account.tesote_id}\n"
                f"Stored cursor: {cursor!r}\n"
                f"Cursor type: {type(cursor).__name__}\n"
                f"Is cursor falsy: {not cursor}"
            )

            if not cursor:
                # Don't use any cursor for initial sync - let it be None/null
                cursor = None
                _logger.info("No stored cursor, omitting cursor for initial sync")

            # Call v2 sync endpoint with retry logic for historical sync forbidden
            _logger.info(f"Calling sync_transactions with cursor: {cursor!r}")
            try:
                sync_result = adapter.sync_transactions(
                    tesote_account_id=account.tesote_id, cursor=cursor, count=100
                )
            except UserError as e:
                error_msg = str(e)
                # Check if this is a HISTORY_SYNC_FORBIDDEN error
                if error_msg == "HISTORY_SYNC_FORBIDDEN:SKIP":
                    _logger.info(
                        f"Historical sync forbidden for account {account.name}. "
                        f"Skipping historical data - will sync new transactions going forward."
                    )
                    # Create empty sync result to continue
                    sync_result = {
                        "added": [],
                        "modified": [],
                        "removed": [],
                        "next_cursor": None,
                        "has_more": False,
                    }
                    # Mark account as synced so future syncs will work
                    account.sync_cursor = "synced_without_history"
                else:
                    # Re-raise other errors
                    raise

            # Process results
            added_count = len(sync_result.get("added", []))
            modified_count = len(sync_result.get("modified", []))
            removed_count = len(sync_result.get("removed", []))

            total_added += added_count
            total_modified += modified_count
            total_removed += removed_count

            # Process transactions
            self._process_sync_results(account, sync_result)

            # Update cursor and sync date for next sync
            if sync_result.get("next_cursor"):
                account.sync_cursor = sync_result["next_cursor"]

            # Update account sync date
            account.sync_date = fields.Datetime.now()

            _logger.info(
                f"Synced account {account.name}: +{added_count} ~{modified_count} -{removed_count}"
            )

        self.last_sync_date = fields.Datetime.now()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sync Complete"),
                "message": _(
                    "Transactions synced: "
                    "%(added)d added, %(modified)d modified, %(removed)d removed"
                )
                % {"added": total_added, "modified": total_modified, "removed": total_removed},
                "type": "success",
                "sticky": False,
            },
        }

    def _process_sync_results(self, account, sync_result):
        """
        Process sync results from v2 API.

        Args:
            account: tesote.account record
            sync_result: Sync response from API
        """
        TesoteTransaction = self.env["tesote.transaction"]

        # Process removed transactions first
        for removed in sync_result.get("removed", []):
            transaction = TesoteTransaction.search(
                [("tesote_id", "=", removed["transaction_id"]), ("account_id", "=", account.id)]
            )
            if transaction:
                transaction.unlink()
                _logger.info(f"Removed transaction {removed['transaction_id']}")

        # Process modified transactions
        for modified in sync_result.get("modified", []):
            transaction = TesoteTransaction.search(
                [("tesote_id", "=", modified["transaction_id"]), ("account_id", "=", account.id)]
            )
            if transaction:
                transaction.update_from_sync_data(modified)
                _logger.info(f"Updated transaction {modified['transaction_id']}")

        # Process added transactions
        for added in sync_result.get("added", []):
            # Check if already exists (shouldn't happen but be safe)
            existing = TesoteTransaction.search(
                [("tesote_id", "=", added["transaction_id"]), ("account_id", "=", account.id)]
            )
            if not existing:
                TesoteTransaction.create_from_sync_data(account, added)
                _logger.info(f"Added transaction {added['transaction_id']}")

    def import_transactions(self, account_ids=None, date_from=None, date_to=None):
        """
        Import transactions for specified accounts (legacy v1 method).

        Prefer sync_transactions_v2 for v2 API.

        Args:
            account_ids: List of tesote.account IDs
            date_from: Start date for transaction import
            date_to: End date for transaction import
        """
        # Use v2 sync instead
        return self.sync_transactions_v2(account_ids)

    @api.model
    def _scheduler_import_accounts(self):
        """Scheduled job to import accounts."""
        backends = self.search([("active", "=", True), ("auto_sync_enabled", "=", True)])
        for backend in backends:
            try:
                backend.import_accounts()
            except Exception as e:
                _logger.error(f"Failed to import accounts for backend {backend.name}: {str(e)}")

    @api.model
    def _scheduler_sync_transactions(self):
        """Scheduled job to sync all data (accounts + transactions)."""
        backends = self.search([("active", "=", True), ("auto_sync_enabled", "=", True)])
        for backend in backends:
            try:
                # Start full sync in background (accounts first, then transactions)
                threading.Thread(
                    target=backend._scheduled_full_sync_background, args=(backend.id,), daemon=True
                ).start()
                _logger.info(f"Started scheduled full sync for backend {backend.name}")
            except Exception as e:
                _logger.error(
                    f"Failed to start scheduled sync for backend {backend.name}: {str(e)}"
                )

    @api.model
    def _scheduler_import_transactions(self):
        """Legacy scheduled job - use _scheduler_sync_transactions instead."""
        return self._scheduler_sync_transactions()
