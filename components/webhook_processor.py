from datetime import datetime, timedelta

from odoo import fields

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="webhook")


class WebhookProcessor:
    """
    Process webhook events from tesote.com API.

    This component handles the async processing of webhook events,
    routing them to appropriate handlers and managing retries.
    """

    def __init__(self, env):
        self.env = env
        self.max_retries = 3
        self.retry_delays = [60, 300, 900]  # 1 min, 5 min, 15 min

    def process_event(self, webhook_event_id):
        """
        Main entry point for processing a webhook event.

        :param webhook_event_id: ID of the webhook event to process
        :return: Boolean indicating success
        """
        WebhookEvent = self.env["tesote.webhook.event"].sudo()
        webhook_event = WebhookEvent.browse(webhook_event_id)

        if not webhook_event.exists():
            _logger.error(f"Webhook event {webhook_event_id} not found")
            return False

        try:
            webhook_event.log_processing_start()

            payload_data = webhook_event.get_payload_data()

            if webhook_event.event_type == "sync.updates_available":
                self._handle_sync_updates(webhook_event, payload_data)
            elif webhook_event.event_type == "accounts.created":
                self._handle_account_created(webhook_event, payload_data)
            elif webhook_event.event_type == "accounts.updated":
                self._handle_account_updated(webhook_event, payload_data)
            elif webhook_event.event_type == "transactions.created":
                self._handle_transaction_created(webhook_event, payload_data)
            elif webhook_event.event_type == "transactions.updated":
                self._handle_transaction_updated(webhook_event, payload_data)
            else:
                raise ValueError(f"Unknown event type: {webhook_event.event_type}")

            webhook_event.log_processing_complete()
            return True

        except Exception as e:
            _logger.error(f"Error processing webhook {webhook_event_id}: {e}", exc_info=True)
            webhook_event.log_processing_error(str(e))

            if self._should_retry(webhook_event):
                self._schedule_retry(webhook_event)

            return False

    def _handle_sync_updates(self, webhook_event, payload_data):
        """
        Handle sync.updates_available webhook event.

        This triggers a background sync job for the specified account,
        reusing the existing sync infrastructure.

        Phase 3 Implementation:
        - Extracts account_id from webhook payload
        - Uses existing sync infrastructure from adapter.py
        - Calls POST /api/v2/transactions/sync with stored cursor
        - Processes added/modified/removed arrays from response
        """
        data = payload_data.get("data", {})
        account_id = data.get("id")

        if not account_id:
            raise ValueError("Missing account ID in sync.updates_available payload")

        TesoteAccount = self.env["tesote.account"].sudo()
        account = TesoteAccount.search(
            [
                ("tesote_id", "=", account_id),  # Changed from 'external_id' to 'tesote_id'
                ("backend_id", "=", webhook_event.backend_id.id),
            ],
            limit=1,
        )

        if not account:
            _logger.warning(f"Account {account_id} not found, attempting to fetch from API")
            self._fetch_and_create_account(account_id, webhook_event.backend_id)
            account = TesoteAccount.search(
                [
                    ("tesote_id", "=", account_id),  # Changed from 'external_id' to 'tesote_id'
                    ("backend_id", "=", webhook_event.backend_id.id),
                ],
                limit=1,
            )

            if not account:
                raise ValueError(f"Could not find or create account {account_id}")

        # Extract sync statistics from webhook payload
        new_count = data.get("new_transactions", 0)
        modified_count = data.get("modified_transactions", 0)
        removed_count = data.get("removed_transactions", 0)

        # Also extract the IDs if provided (useful for debugging)
        new_ids = data.get("new_ids", [])
        updated_ids = data.get("updated_ids", [])
        removed_ids = data.get("removed_ids", [])

        _logger.info(
            f"Processing sync.updates_available for account {account_id}: "
            f"new={new_count}, modified={modified_count}, removed={removed_count}"
        )

        if new_ids or updated_ids or removed_ids:
            _logger.debug(
                f"Transaction IDs - New: {new_ids}, Updated: {updated_ids}, Removed: {removed_ids}"
            )

        # Get the backend and trigger sync using the backend's sync method
        backend = webhook_event.backend_id

        # Use the backend's sync_transactions_v2 method which handles cursor-based sync
        if hasattr(backend, "with_delay"):
            # Queue the sync job for async processing
            job = backend.with_delay(
                priority=5,
                max_retries=3,
                description=f"Sync transactions for account {account.name} (webhook triggered)",
            ).sync_transactions_v2(account_ids=[account.id])

            if hasattr(job, "uuid"):
                webhook_event.sync_job_id = str(job.uuid)
                _logger.info(f"Queued sync job {job.uuid} for account {account_id}")
        else:
            # Execute sync directly if queue_job is not available
            backend.sync_transactions_v2(account_ids=[account.id])
            _logger.info(f"Executed direct sync for account {account_id}")

    def _handle_account_created(self, webhook_event, payload_data):
        """Handle accounts.created webhook event."""
        data = payload_data.get("data", {})
        account_id = data.get("id")

        if not account_id:
            raise ValueError("Missing account ID in accounts.created payload")

        TesoteAccount = self.env["tesote.account"].sudo()
        existing = TesoteAccount.search(
            [("tesote_id", "=", account_id), ("backend_id", "=", webhook_event.backend_id.id)],
            limit=1,
        )

        if existing:
            _logger.info(f"Account {account_id} already exists, updating instead")
            self._update_account_from_data(existing, data)
            return

        account_vals = self._prepare_account_values(data, webhook_event.backend_id)
        new_account = TesoteAccount.create(account_vals)

        _logger.info(f"Created account {new_account.name} (ID: {account_id}) from webhook")

        if data.get("sync_required", False):
            _logger.info(f"Account {account_id} requires initial sync")
            backend = webhook_event.backend_id
            if hasattr(backend, "with_delay"):
                backend.with_delay(
                    priority=10, description=f"Initial sync for new account {new_account.name}"
                ).sync_transactions_v2(account_ids=[new_account.id])
            else:
                backend.sync_transactions_v2(account_ids=[new_account.id])

    def _handle_account_updated(self, webhook_event, payload_data):
        """Handle accounts.updated webhook event."""
        data = payload_data.get("data", {})
        account_id = data.get("id")

        if not account_id:
            raise ValueError("Missing account ID in accounts.updated payload")

        TesoteAccount = self.env["tesote.account"].sudo()
        account = TesoteAccount.search(
            [("tesote_id", "=", account_id), ("backend_id", "=", webhook_event.backend_id.id)],
            limit=1,
        )

        if not account:
            _logger.warning(f"Account {account_id} not found for update, creating it")
            account_vals = self._prepare_account_values(data, webhook_event.backend_id)
            account = TesoteAccount.create(account_vals)
            _logger.info(f"Created account {account.name} from update webhook")
        else:
            self._update_account_from_data(account, data)
            _logger.info(f"Updated account {account.name} (ID: {account_id}) from webhook")

        if data.get("balance_changed", False):
            _logger.info(f"Account {account_id} balance changed, triggering sync")
            backend = webhook_event.backend_id
            if hasattr(backend, "with_delay"):
                backend.with_delay(
                    priority=8, description=f"Sync after balance change for {account.name}"
                ).sync_transactions_v2(account_ids=[account.id])
            else:
                backend.sync_transactions_v2(account_ids=[account.id])

    def _handle_transaction_created(self, webhook_event, payload_data):
        """Handle transactions.created webhook event."""
        data = payload_data.get("data", {})
        transaction_id = data.get("id")
        account_id = data.get("account_id")

        if not transaction_id or not account_id:
            raise ValueError("Missing transaction or account ID in payload")

        TesoteAccount = self.env["tesote.account"].sudo()
        account = TesoteAccount.search(
            [("tesote_id", "=", account_id), ("backend_id", "=", webhook_event.backend_id.id)],
            limit=1,
        )

        if not account:
            _logger.warning(f"Account {account_id} not found for new transaction")
            return

        TesoteTransaction = self.env["tesote.transaction"].sudo()
        existing = TesoteTransaction.search(
            [("tesote_id", "=", transaction_id), ("account_id", "=", account.id)], limit=1
        )

        if existing:
            _logger.info(f"Transaction {transaction_id} already exists")
            return

        transaction_vals = self._prepare_transaction_values(data, account)
        new_transaction = TesoteTransaction.create(transaction_vals)

        _logger.info(
            f"Created transaction {new_transaction.name} "
            f"(ID: {transaction_id}) for account {account.name}"
        )

    def _handle_transaction_updated(self, webhook_event, payload_data):
        """Handle transactions.updated webhook event."""
        data = payload_data.get("data", {})
        transaction_id = data.get("id")

        if not transaction_id:
            raise ValueError("Missing transaction ID in payload")

        TesoteTransaction = self.env["tesote.transaction"].sudo()
        transaction = TesoteTransaction.search([("tesote_id", "=", transaction_id)], limit=1)

        if not transaction:
            _logger.warning(f"Transaction {transaction_id} not found for update")
            return

        update_vals = {}

        if "status" in data:
            update_vals["status"] = data["status"]
        if "amount" in data:
            update_vals["amount"] = data["amount"]
        if "description" in data:
            update_vals["description"] = data["description"]
        if "category" in data:
            update_vals["category"] = data["category"]
        if "merchant_name" in data:
            update_vals["merchant_name"] = data["merchant_name"]

        if update_vals:
            transaction.write(update_vals)
            _logger.info(f"Updated transaction {transaction.name} (ID: {transaction_id})")

    def _prepare_account_values(self, data, backend):
        """Prepare account values from webhook data."""
        return {
            "tesote_id": data.get("id"),
            "backend_id": backend.id,
            "name": data.get("name", f"Account {data.get('id')}"),
            "account_type": data.get("type", "checking"),
            "balance": data.get("balance", 0.0),
            "currency": data.get("currency", "USD"),
            "institution_name": data.get("institution_name", ""),
            "active": data.get("active", True),
            "last_sync": fields.Datetime.now() if data.get("sync_required") else False,
        }

    def _update_account_from_data(self, account, data):
        """Update account fields from webhook data."""
        update_vals = {}

        if "name" in data and data["name"] != account.name:
            update_vals["name"] = data["name"]
        if "balance" in data and data["balance"] != account.balance:
            update_vals["balance"] = data["balance"]
        if "type" in data and data["type"] != account.account_type:
            update_vals["account_type"] = data["type"]
        if "institution_name" in data and data["institution_name"] != account.institution_name:
            update_vals["institution_name"] = data["institution_name"]
        if "active" in data and data["active"] != account.active:
            update_vals["active"] = data["active"]

        if update_vals:
            account.write(update_vals)

    def _prepare_transaction_values(self, data, account):
        """Prepare transaction values from webhook data."""
        transaction_date = data.get("date")
        if transaction_date:
            try:
                transaction_date = datetime.fromisoformat(
                    transaction_date.replace("Z", "+00:00")
                ).date()
            except (ValueError, AttributeError):
                transaction_date = fields.Date.today()
        else:
            transaction_date = fields.Date.today()

        return {
            "tesote_id": data.get("id"),
            "account_id": account.id,
            "name": data.get("description", f"Transaction {data.get('id')}"),
            "date": transaction_date,
            "amount": data.get("amount", 0.0),
            "status": data.get("status", "pending"),
            "category": data.get("category", ""),
            "merchant_name": data.get("merchant_name", ""),
            "description": data.get("description", ""),
            "transaction_type": data.get("type", "debit"),
        }

    def _fetch_and_create_account(self, account_id, backend):
        """Fetch account from API and create it."""
        try:
            from components.adapter import TesoteAdapter

            adapter = TesoteAdapter(self.env)
            adapter.backend = backend

            response = adapter._call_api(f"/accounts/{account_id}", method="GET")

            if response and response.get("data"):
                account_data = response["data"]
                account_vals = self._prepare_account_values(account_data, backend)
                TesoteAccount = self.env["tesote.account"].sudo()
                return TesoteAccount.create(account_vals)
        except Exception as e:
            _logger.error(f"Failed to fetch account {account_id} from API: {e}")
            return None

    def _should_retry(self, webhook_event):
        """Determine if webhook should be retried based on retry count."""
        return webhook_event.retry_count < self.max_retries

    def _schedule_retry(self, webhook_event):
        """Schedule a retry for failed webhook processing."""
        retry_count = webhook_event.retry_count
        if retry_count >= len(self.retry_delays):
            delay_seconds = self.retry_delays[-1]
        else:
            delay_seconds = self.retry_delays[retry_count]

        eta = datetime.now() + timedelta(seconds=delay_seconds)

        _logger.info(
            f"Scheduling retry #{retry_count + 1} for webhook {webhook_event.event_id} "
            f"at {eta.isoformat()}"
        )

        if hasattr(webhook_event, "with_delay"):
            webhook_event.with_delay(
                eta=eta,
                priority=20,
                description=f"Retry #{retry_count + 1} for webhook {webhook_event.event_id}",
            ).process_webhook()
        else:
            _logger.warning("Queue job not available, cannot schedule retry")

    def process_pending_events(self, limit=100):
        """
        Process all pending webhook events.

        This can be called from a cron job to process any events
        that might have been missed.
        """
        WebhookEvent = self.env["tesote.webhook.event"].sudo()
        pending_events = WebhookEvent.search(
            [("status", "=", "pending")], limit=limit, order="received_at asc"
        )

        processed = 0
        failed = 0

        for event in pending_events:
            try:
                if self.process_event(event.id):
                    processed += 1
                else:
                    failed += 1
            except Exception as e:
                _logger.error(f"Error processing pending event {event.id}: {e}")
                failed += 1

        _logger.info(f"Processed {processed} pending events, {failed} failed")
        return {"processed": processed, "failed": failed}
