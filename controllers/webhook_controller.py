import json
from datetime import datetime

from odoo import http
from odoo.http import request

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="webhook")


class TesoteWebhookController(http.Controller):
    """Controller to handle incoming webhooks from tesote.com."""

    @http.route("/tesote/webhook", type="json", auth="public", methods=["POST"], csrf=False)
    def webhook_endpoint(self, **kwargs):
        """
        Main webhook endpoint for receiving tesote.com webhooks.

        Response time requirement: < 5 seconds
        Returns: HTTP 200 on success, appropriate error code on failure
        """
        start_time = datetime.now()

        try:
            # Get the singleton backend
            backend = request.env["tesote.backend"].sudo().search([], limit=1)
            if not backend:
                _logger.error("No Tesote backend configured")
                return {"status": "error", "message": "No backend configured"}

            # Get webhook configuration for the singleton backend
            webhook_config = (
                request.env["tesote.webhook.config"]
                .sudo()
                .search([("backend_id", "=", backend.id), ("enabled", "=", True)], limit=1)
            )

            if not webhook_config:
                _logger.warning("Webhook received but webhook configuration is not enabled")
                return {"status": "error", "message": "Webhook not configured"}

            # Extract webhook headers
            headers = request.httprequest.headers
            event_id = headers.get("X-Tesote-Webhook-Id")
            event_type = headers.get("X-Tesote-Event-Type")
            signature = headers.get("X-Tesote-Signature")
            timestamp = headers.get("X-Tesote-Timestamp")

            if not all([event_id, event_type, signature, timestamp]):
                _logger.error("Missing required webhook headers")
                return {"status": "error", "message": "Missing required headers"}

            # Get request body
            raw_body = request.httprequest.data

            # Verify signature (Task 4.1)
            if not webhook_config.verify_signature(raw_body, timestamp, signature):
                _logger.error(f"Invalid webhook signature for backend {backend.id}")
                return {"status": "error", "message": "Invalid signature"}

            # Check idempotency (Task 4.2)
            WebhookEvent = request.env["tesote.webhook.event"].sudo()
            if WebhookEvent.check_idempotency(event_id):
                _logger.info(f"Duplicate webhook {event_id} - already processed")
                return {"status": "success", "message": "Already processed"}

            # Parse payload
            try:
                if isinstance(raw_body, bytes):
                    payload_str = raw_body.decode("utf-8")
                else:
                    payload_str = raw_body
                json.loads(payload_str)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                _logger.error(f"Failed to parse webhook payload: {e}")
                return {"status": "error", "message": "Invalid payload"}

            # Check if event type is subscribed
            active_events = webhook_config.get_active_events()
            if event_type not in active_events:
                _logger.info(f"Received unsubscribed event type: {event_type}")
                return {"status": "success", "message": "Event not subscribed"}

            # Create webhook event record (stored immediately for async processing)
            webhook_event = WebhookEvent.create(
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "payload": payload_str,
                    "headers": json.dumps(dict(headers)),
                    "signature": signature,
                    "timestamp": timestamp,
                    "backend_id": backend.id,
                    "status": "pending",
                    "ip_address": request.httprequest.remote_addr,
                }
            )

            # Log receipt
            webhook_event.log_webhook_receipt(request)

            # Update webhook stats
            webhook_config.update_webhook_stats()

            # Queue background job for async processing
            self._queue_webhook_processing(webhook_event)

            # Calculate response time
            response_time = (datetime.now() - start_time).total_seconds()
            _logger.info(f"Webhook {event_id} accepted in {response_time:.3f}s")

            # Return success immediately (< 5 seconds requirement)
            return {"status": "success", "event_id": event_id}

        except Exception as e:
            _logger.error(f"Unexpected error processing webhook: {e}", exc_info=True)
            return {"status": "error", "message": "Internal server error"}

    def _queue_webhook_processing(self, webhook_event):
        """
        Queue webhook for background processing.

        This method triggers async processing to handle the webhook
        without blocking the HTTP response.
        """
        try:
            # Use the WebhookProcessor for handling the event
            from ..components.webhook_processor import WebhookProcessor

            # Check if queue_job module is installed
            if hasattr(webhook_event, "with_delay"):
                # Use queue_job for async processing if available
                webhook_event.with_delay(
                    priority=5,
                    max_retries=3,
                    description=f"Process webhook {webhook_event.event_id} ({webhook_event.event_type})",
                ).process_webhook()
            else:
                # Fall back to immediate processing (still within 5 second window)
                # In production, you should use queue_job or similar
                processor = WebhookProcessor(webhook_event.env)
                processor.process_event(webhook_event.id)

        except Exception as e:
            _logger.error(f"Failed to queue webhook processing: {e}")
            webhook_event.log_processing_error(str(e))

    @http.route("/tesote/webhook/test", type="http", auth="user", methods=["GET"])
    def test_webhook(self, **kwargs):
        """Test endpoint to verify webhook setup."""
        return json.dumps(
            {
                "status": "ok",
                "message": "Tesote webhook endpoint is configured",
                "timestamp": datetime.now().isoformat(),
            }
        )
