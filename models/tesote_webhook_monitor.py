import json
from datetime import datetime, timedelta

from odoo import _, api, fields, models

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="webhook")


class TesoteWebhookMonitor(models.Model):
    _name = "tesote.webhook.monitor"
    _description = "Tesote Webhook Monitoring"
    _order = "date desc"
    _rec_name = "date"

    # Date/Time fields
    date = fields.Date(string="Date", required=True, default=fields.Date.today, index=True)
    hour = fields.Integer(string="Hour", help="Hour of the day (0-23)")

    # Metrics
    total_received = fields.Integer(string="Total Received", default=0)
    total_processed = fields.Integer(string="Total Processed", default=0)
    total_failed = fields.Integer(string="Total Failed", default=0)
    total_retried = fields.Integer(string="Total Retried", default=0)

    # Success metrics
    success_rate = fields.Float(
        string="Success Rate",
        compute="_compute_success_rate",
        store=True,
        help="Percentage of successfully processed webhooks",
    )

    # Performance metrics
    avg_processing_time = fields.Float(string="Avg Processing Time (ms)", default=0.0)
    max_processing_time = fields.Float(string="Max Processing Time (ms)", default=0.0)
    min_processing_time = fields.Float(string="Min Processing Time (ms)", default=0.0)

    # Breakdown by event type
    metrics_by_type = fields.Text(
        string="Metrics by Type", help="JSON containing metrics broken down by event type"
    )

    # Signature validation metrics
    signature_failures = fields.Integer(string="Signature Failures", default=0)

    # Alert tracking
    alerts_triggered = fields.Integer(string="Alerts Triggered", default=0)

    # Backend reference
    backend_id = fields.Many2one(
        "tesote.backend", string="Backend", required=True, ondelete="cascade"
    )

    @api.depends("total_received", "total_processed")
    def _compute_success_rate(self):
        for record in self:
            if record.total_received > 0:
                record.success_rate = (record.total_processed / record.total_received) * 100
            else:
                record.success_rate = 0.0

    @api.model
    def update_metrics(self, webhook_event):
        """Update monitoring metrics when a webhook event is processed"""
        backend = webhook_event.webhook_config_id.backend_id
        today = fields.Date.today()
        current_hour = datetime.now().hour

        # Find or create today's monitor record
        monitor = self.search(
            [("date", "=", today), ("hour", "=", current_hour), ("backend_id", "=", backend.id)],
            limit=1,
        )

        if not monitor:
            monitor = self.create(
                {
                    "date": today,
                    "hour": current_hour,
                    "backend_id": backend.id,
                    "metrics_by_type": json.dumps({}),
                }
            )

        # Update counters
        monitor.total_received += 1

        if webhook_event.status == "completed":
            monitor.total_processed += 1
        elif webhook_event.status == "failed":
            monitor.total_failed += 1

        if webhook_event.retry_count > 0:
            monitor.total_retried += 1

        # Update processing time metrics
        if webhook_event.processing_duration:
            if (
                monitor.min_processing_time == 0
                or webhook_event.processing_duration < monitor.min_processing_time
            ):
                monitor.min_processing_time = webhook_event.processing_duration
            if webhook_event.processing_duration > monitor.max_processing_time:
                monitor.max_processing_time = webhook_event.processing_duration

            # Calculate new average
            total_processed = monitor.total_processed or 1
            current_total = monitor.avg_processing_time * (total_processed - 1)
            monitor.avg_processing_time = (
                current_total + webhook_event.processing_duration
            ) / total_processed

        # Update signature failure count
        if hasattr(webhook_event, "signature_valid") and not webhook_event.signature_valid:
            monitor.signature_failures += 1

        # Update metrics by type
        metrics_by_type = json.loads(monitor.metrics_by_type or "{}")
        event_type = webhook_event.event_type

        if event_type not in metrics_by_type:
            metrics_by_type[event_type] = {
                "received": 0,
                "processed": 0,
                "failed": 0,
                "avg_time": 0.0,
            }

        metrics_by_type[event_type]["received"] += 1

        if webhook_event.status == "completed":
            metrics_by_type[event_type]["processed"] += 1
        elif webhook_event.status == "failed":
            metrics_by_type[event_type]["failed"] += 1

        if webhook_event.processing_duration:
            current_avg = metrics_by_type[event_type]["avg_time"]
            count = metrics_by_type[event_type]["processed"] or 1
            metrics_by_type[event_type]["avg_time"] = (
                current_avg * (count - 1) + webhook_event.processing_duration
            ) / count

        monitor.metrics_by_type = json.dumps(metrics_by_type)

        return monitor

    @api.model
    def check_alert_conditions(self):
        """Check for conditions that should trigger alerts"""
        alerts = []

        # Check failure rate in last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_monitors = self.search(
            [("date", "=", fields.Date.today()), ("hour", "=", one_hour_ago.hour)]
        )

        for monitor in recent_monitors:
            config = monitor.backend_id.webhook_config_ids[:1]
            if not config or not config.alert_on_failure:
                continue

            # Check if failure rate exceeds threshold
            failure_rate = 100 - monitor.success_rate
            if failure_rate > config.alert_threshold:
                alerts.append(
                    {
                        "type": "high_failure_rate",
                        "backend": monitor.backend_id.name,
                        "failure_rate": failure_rate,
                        "threshold": config.alert_threshold,
                        "hour": monitor.hour,
                        "date": monitor.date,
                    }
                )
                monitor.alerts_triggered += 1

        # Check for signature failures
        for monitor in recent_monitors:
            if monitor.signature_failures > 5:
                alerts.append(
                    {
                        "type": "signature_failures",
                        "backend": monitor.backend_id.name,
                        "count": monitor.signature_failures,
                        "hour": monitor.hour,
                        "date": monitor.date,
                    }
                )
                monitor.alerts_triggered += 1

        return alerts

    @api.model
    def send_alert_notifications(self, alerts):
        """Send alert notifications to configured recipients"""
        for alert in alerts:
            backend = self.env["tesote.backend"].search([("name", "=", alert["backend"])], limit=1)

            if not backend:
                continue

            config = backend.webhook_config_ids[:1]
            if not config or not config.alert_email_to:
                continue

            # Prepare email content
            if alert["type"] == "high_failure_rate":
                subject = _("[Alert] High Webhook Failure Rate - %s") % backend.name
                body = _(
                    """
                    <p>High webhook failure rate detected:</p>
                    <ul>
                        <li>Backend: %s</li>
                        <li>Failure Rate: %.2f%%</li>
                        <li>Threshold: %.2f%%</li>
                        <li>Time: %s %s:00</li>
                    </ul>
                """
                ) % (
                    alert["backend"],
                    alert["failure_rate"],
                    alert["threshold"],
                    alert["date"],
                    alert["hour"],
                )
            elif alert["type"] == "signature_failures":
                subject = _("[Alert] Multiple Webhook Signature Failures - %s") % backend.name
                body = _(
                    """
                    <p>Multiple webhook signature validation failures detected:</p>
                    <ul>
                        <li>Backend: %s</li>
                        <li>Failed Signatures: %d</li>
                        <li>Time: %s %s:00</li>
                    </ul>
                    <p>Please check your webhook secret configuration.</p>
                """
                ) % (alert["backend"], alert["count"], alert["date"], alert["hour"])
            else:
                continue

            # Send email
            mail_values = {
                "subject": subject,
                "body_html": body,
                "email_to": config.alert_email_to,
                "email_from": self.env.company.email or "noreply@localhost",
            }

            self.env["mail.mail"].create(mail_values).send()
            _logger.info(
                "Alert notification sent to %s for %s", config.alert_email_to, alert["type"]
            )

    @api.model
    def generate_daily_report(self):
        """Generate daily webhook performance report"""
        yesterday = fields.Date.today() - timedelta(days=1)
        monitors = self.search([("date", "=", yesterday)])

        if not monitors:
            return None

        # Aggregate metrics
        total_received = sum(m.total_received for m in monitors)
        total_processed = sum(m.total_processed for m in monitors)
        total_failed = sum(m.total_failed for m in monitors)

        # Calculate overall success rate
        success_rate = (total_processed / total_received * 100) if total_received > 0 else 0

        # Find peak hour
        peak_hour = max(monitors, key=lambda m: m.total_received)

        # Aggregate by event type
        type_metrics = {}
        for monitor in monitors:
            if monitor.metrics_by_type:
                metrics = json.loads(monitor.metrics_by_type)
                for event_type, data in metrics.items():
                    if event_type not in type_metrics:
                        type_metrics[event_type] = {"received": 0, "processed": 0, "failed": 0}
                    type_metrics[event_type]["received"] += data["received"]
                    type_metrics[event_type]["processed"] += data["processed"]
                    type_metrics[event_type]["failed"] += data["failed"]

        report = {
            "date": yesterday,
            "total_received": total_received,
            "total_processed": total_processed,
            "total_failed": total_failed,
            "success_rate": success_rate,
            "peak_hour": peak_hour.hour,
            "peak_hour_volume": peak_hour.total_received,
            "type_metrics": type_metrics,
            "signature_failures": sum(m.signature_failures for m in monitors),
            "alerts_triggered": sum(m.alerts_triggered for m in monitors),
        }

        return report

    @api.model
    def cleanup_old_monitors(self, days=90):
        """Clean up monitor records older than specified days"""
        cutoff_date = fields.Date.today() - timedelta(days=days)
        old_monitors = self.search([("date", "<", cutoff_date)])

        if old_monitors:
            _logger.info("Cleaning up %d old webhook monitor records", len(old_monitors))
            old_monitors.unlink()

        return len(old_monitors)

    @api.model
    def update_recent_metrics(self):
        """Update metrics for recent webhook events (last 10 minutes)"""
        cutoff_time = fields.Datetime.now() - timedelta(minutes=10)
        recent_events = self.env["tesote.webhook.event"].search(
            [("received_at", ">=", cutoff_time), ("status", "in", ["completed", "failed"])]
        )

        for event in recent_events:
            self.update_metrics(event)

    def get_hourly_chart_data(self):
        """Get data for hourly chart visualization"""
        self.ensure_one()

        # Get all monitors for the day
        monitors = self.search(
            [("date", "=", self.date), ("backend_id", "=", self.backend_id.id)], order="hour"
        )

        labels = []
        received_data = []
        processed_data = []
        failed_data = []

        for hour in range(24):
            labels.append(f"{hour:02d}:00")
            monitor = monitors.filtered(lambda m: m.hour == hour)
            if monitor:
                received_data.append(monitor.total_received)
                processed_data.append(monitor.total_processed)
                failed_data.append(monitor.total_failed)
            else:
                received_data.append(0)
                processed_data.append(0)
                failed_data.append(0)

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Received",
                    "data": received_data,
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                },
                {
                    "label": "Processed",
                    "data": processed_data,
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "borderColor": "rgba(75, 192, 192, 1)",
                },
                {
                    "label": "Failed",
                    "data": failed_data,
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                },
            ],
        }
