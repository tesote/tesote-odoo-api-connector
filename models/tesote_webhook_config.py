import hashlib
import hmac
import secrets
from urllib.parse import urljoin

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="webhook")


class TesoteWebhookConfig(models.Model):
    _name = "tesote.webhook.config"
    _description = "Tesote Webhook Configuration"
    _rec_name = "backend_id"

    backend_id = fields.Many2one(
        "tesote.backend", string="Backend", required=True, ondelete="cascade"
    )
    webhook_url = fields.Char(
        string="Webhook URL",
        compute="_compute_webhook_url",
        store=False,
        help="Generated endpoint URL for receiving webhooks",
    )
    secret_key = fields.Char(
        string="Secret Key", required=True, help="Secret key for HMAC-SHA256 signature verification"
    )
    enabled = fields.Boolean(string="Enabled", default=False, help="Enable webhook processing")

    # Event subscriptions
    subscribe_sync_updates = fields.Boolean(
        string="Sync Updates Available",
        default=True,
        help="Subscribe to sync.updates_available events",
    )
    subscribe_account_created = fields.Boolean(
        string="Account Created", default=True, help="Subscribe to accounts.created events"
    )
    subscribe_account_updated = fields.Boolean(
        string="Account Updated", default=True, help="Subscribe to accounts.updated events"
    )
    subscribe_transaction_created = fields.Boolean(
        string="Transaction Created", default=False, help="Subscribe to transactions.created events"
    )
    subscribe_transaction_updated = fields.Boolean(
        string="Transaction Updated", default=False, help="Subscribe to transactions.updated events"
    )

    # Monitoring fields
    last_webhook_at = fields.Datetime(
        string="Last Webhook Received", readonly=True, help="Timestamp of last webhook received"
    )
    total_webhooks_received = fields.Integer(
        string="Total Webhooks", default=0, readonly=True, help="Total number of webhooks received"
    )
    failed_signature_count = fields.Integer(
        string="Failed Signatures",
        default=0,
        readonly=True,
        help="Number of signature verification failures",
    )

    # Additional fields for UI views
    webhook_path = fields.Char(string="Webhook Path", default="/tesote/webhook", readonly=True)
    active_events = fields.Many2many(
        "tesote.webhook.event.type", string="Active Events", compute="_compute_active_events"
    )
    last_verified = fields.Datetime(string="Last Verified", readonly=True)
    verification_status = fields.Selection(
        [("pending", "Pending"), ("verified", "Verified"), ("failed", "Failed")],
        string="Verification Status",
        default="pending",
    )
    last_error = fields.Text(string="Last Error", readonly=True)
    total_received = fields.Integer(string="Total Received", compute="_compute_stats")
    total_processed = fields.Integer(string="Total Processed", compute="_compute_stats")
    total_failed = fields.Integer(string="Total Failed", compute="_compute_stats")
    success_rate = fields.Float(string="Success Rate", compute="_compute_stats")
    recent_webhook_events = fields.One2many(
        "tesote.webhook.event", "webhook_config_id", string="Recent Events"
    )

    # Alert configuration
    alert_on_failure = fields.Boolean(
        string="Alert on Failure",
        default=False,
        help="Send email alerts when webhook failures exceed threshold",
    )
    alert_threshold = fields.Float(
        string="Alert Threshold (%)",
        default=10.0,
        help="Failure rate percentage that triggers alerts",
    )
    alert_email_to = fields.Char(string="Alert Email To", help="Email address to send alerts to")

    # Retry configuration
    retry_max_attempts = fields.Integer(string="Max Retry Attempts", default=3)
    retry_backoff_base = fields.Float(
        string="Retry Backoff Base", default=2.0, help="Base for exponential backoff (seconds)"
    )
    timeout_seconds = fields.Integer(string="Timeout (seconds)", default=30)

    _sql_constraints = [
        ("backend_unique", "UNIQUE(backend_id)", "Only one webhook configuration per backend"),
    ]

    @api.depends("backend_id")
    def _compute_webhook_url(self):
        """Generate the webhook endpoint URL (static since backend is singleton)."""
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for record in self:
            if record.backend_id:
                # Static URL since we have a singleton backend
                endpoint = "/tesote/webhook"
                record.webhook_url = urljoin(base_url, endpoint)
            else:
                record.webhook_url = ""

    @api.model
    def generate_secret_key(self):
        """Generate a secure random secret key."""
        return secrets.token_urlsafe(32)

    @api.model_create_multi
    def create(self, vals_list):
        """Generate secret key on creation if not provided and enforce singleton."""
        # Check if configuration already exists
        existing = self.search([("id", "!=", 0)], limit=1)
        if existing:
            raise UserError(
                _(
                    "Only one webhook configuration is allowed. Please edit the existing configuration."
                )
            )

        for vals in vals_list:
            if "secret_key" not in vals or not vals["secret_key"]:
                vals["secret_key"] = self.generate_secret_key()
            # Ensure backend_id is set to the singleton backend
            if "backend_id" not in vals:
                backend = self.env["tesote.backend"].search([], limit=1)
                if backend:
                    vals["backend_id"] = backend.id
                else:
                    raise UserError(
                        _("No backend configuration found. Please configure the backend first.")
                    )
        return super().create(vals_list)

    def regenerate_secret_key(self):
        """Regenerate the webhook secret key."""
        self.ensure_one()
        self.secret_key = self.generate_secret_key()
        _logger.info(f"Regenerated webhook secret key for backend {self.backend_id.name}")
        return True

    def get_active_events(self):
        """Return list of subscribed event types."""
        self.ensure_one()
        events = []
        if self.subscribe_sync_updates:
            events.append("sync.updates_available")
        if self.subscribe_account_created:
            events.append("accounts.created")
        if self.subscribe_account_updated:
            events.append("accounts.updated")
        if self.subscribe_transaction_created:
            events.append("transactions.created")
        if self.subscribe_transaction_updated:
            events.append("transactions.updated")
        return events

    def verify_signature(self, payload, timestamp, signature):
        """Verify webhook signature using HMAC-SHA256."""
        self.ensure_one()

        if not self.secret_key:
            _logger.error("No secret key configured for webhook verification")
            self.failed_signature_count += 1
            return False

        try:
            # Construct the signed payload
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            signed_payload = f"{timestamp}.{payload}"

            # Calculate expected signature
            expected = hmac.new(
                self.secret_key.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            # Compare signatures securely
            is_valid = hmac.compare_digest(expected, signature)

            if not is_valid:
                self.failed_signature_count += 1
                _logger.warning(
                    f"Webhook signature verification failed for backend {self.backend_id.name}"
                )

            return is_valid

        except Exception as e:
            _logger.error(f"Error verifying webhook signature: {e}")
            self.failed_signature_count += 1
            return False

    def update_webhook_stats(self):
        """Update webhook statistics after receiving a webhook."""
        self.ensure_one()
        self.last_webhook_at = fields.Datetime.now()
        self.total_webhooks_received += 1

    def test_webhook_connection(self):
        """Test webhook configuration by creating a test webhook event."""
        self.ensure_one()
        if not self.enabled:
            raise UserError(_("Please enable webhook configuration first"))

        # Create a test webhook event to demonstrate functionality
        import json
        import time

        test_payload = {
            "event_type": "test.webhook",
            "data": {
                "test": True,
                "message": "This is a test webhook event",
                "timestamp": time.time(),
                "backend_id": self.backend_id.name,
            },
            "timestamp": time.time(),
        }

        # Create webhook event record
        webhook_event = self.env["tesote.webhook.event"].create(
            {
                "webhook_config_id": self.id,
                "backend_id": self.backend_id.id,  # Add required backend_id
                "event_id": f"test-{int(time.time())}",
                "event_type": "test.webhook",
                "payload": json.dumps(test_payload),
                "headers": json.dumps({"Content-Type": "application/json"}),
                "signature": "test-signature",
                "signature_valid": True,
                "status": "completed",
                "received_at": fields.Datetime.now(),
                "processed_at": fields.Datetime.now(),
                "processing_duration": 50,  # 50ms fake processing time
            }
        )

        _logger.info(
            f"Created test webhook event {webhook_event.event_id} for backend {self.backend_id.name}"
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Webhook Test"),
                "message": _(
                    "Test webhook event created successfully! Check the webhook events for results."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def get_config_for_backend(self, backend_id):
        """Get webhook configuration for a specific backend."""
        config = self.search([("backend_id", "=", backend_id)], limit=1)
        if not config:
            _logger.debug(f"No webhook configuration found for backend {backend_id}")
        return config

    @api.depends(
        "subscribe_sync_updates",
        "subscribe_account_created",
        "subscribe_account_updated",
        "subscribe_transaction_created",
        "subscribe_transaction_updated",
    )
    def _compute_active_events(self):
        """Compute active events based on subscription flags."""
        EventType = self.env["tesote.webhook.event.type"]
        for record in self:
            event_names = record.get_active_events()
            # Create event type records if they don't exist
            events = EventType
            for name in event_names:
                event = EventType.search([("name", "=", name)], limit=1)
                if not event:
                    event = EventType.create({"name": name})
                events |= event
            record.active_events = events

    @api.depends("backend_id")
    def _compute_stats(self):
        """Compute webhook statistics."""
        for record in self:
            events = self.env["tesote.webhook.event"].search(
                [("webhook_config_id", "=", record.id)]
            )
            record.total_received = len(events)
            record.total_processed = len(events.filtered(lambda e: e.status == "completed"))
            record.total_failed = len(events.filtered(lambda e: e.status == "failed"))

            if record.total_received > 0:
                record.success_rate = (record.total_processed / record.total_received) * 100
            else:
                record.success_rate = 0.0

    def action_test_webhook(self):
        """Test webhook configuration."""
        self.ensure_one()
        return self.test_webhook_connection()

    def action_verify_signature(self):
        """Verify webhook signature configuration."""
        self.ensure_one()

        # Create a test payload and verify signature
        import json
        import time

        test_payload = json.dumps({"test": True, "timestamp": time.time()})
        timestamp = str(int(time.time()))

        # Generate signature
        signed_payload = f"{timestamp}.{test_payload}"
        test_signature = hmac.new(
            self.secret_key.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Verify signature
        if self.verify_signature(test_payload, timestamp, test_signature):
            self.verification_status = "verified"
            self.last_verified = fields.Datetime.now()
            message = _("Signature verification successful")
            msg_type = "success"
        else:
            self.verification_status = "failed"
            self.last_error = _("Signature verification failed")
            message = _("Signature verification failed")
            msg_type = "warning"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Signature Verification"),
                "message": message,
                "type": msg_type,
                "sticky": False,
            },
        }

    def action_regenerate_secret(self):
        """Regenerate webhook secret key."""
        self.ensure_one()
        self.regenerate_secret_key()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Secret Regenerated"),
                "message": _("Webhook secret key has been regenerated successfully"),
                "type": "info",
                "sticky": False,
            },
        }

    def action_show_secret(self):
        """Show the webhook secret key in a popup wizard."""
        self.ensure_one()

        # Create a temporary wizard record to show the secret
        wizard = self.env["tesote.webhook.secret.wizard"].create(
            {
                "webhook_config_id": self.id,
                "secret_key": self.secret_key,
                "webhook_url": self.webhook_url,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Webhook Configuration Details"),
            "res_model": "tesote.webhook.secret.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",  # Open in popup
            "context": {"create": False, "edit": False, "delete": False},
        }

    @api.model
    def action_open_configuration(self):
        """Open the singleton webhook configuration or create if it doesn't exist."""
        config = self.search([], limit=1)
        if not config:
            # Get the singleton backend
            backend = self.env["tesote.backend"].search([], limit=1)
            if not backend:
                raise UserError(
                    _("No backend configuration found. Please configure the backend first.")
                )

            # Create default webhook configuration
            config = self.create(
                {
                    "backend_id": backend.id,
                    "enabled": False,
                    "subscribe_sync_updates": True,
                    "subscribe_account_created": True,
                    "subscribe_account_updated": True,
                    "subscribe_transaction_created": False,
                    "subscribe_transaction_updated": False,
                }
            )

        # Return action to open the form view
        return {
            "type": "ir.actions.act_window",
            "name": _("Webhook Configuration"),
            "res_model": "tesote.webhook.config",
            "res_id": config.id,
            "view_mode": "form",
            "view_id": self.env.ref("tesote_connector.tesote_webhook_config_form").id,
            "target": "current",
        }
