import hashlib
import hmac
import json

from odoo import http
from odoo.http import request

# Handle both package and direct imports for testing
try:
    from ...utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

try:
    from ...utils.sentry_config import capture_exception
except ImportError:
    from utils.sentry_config import capture_exception

_logger = get_logger(__name__, category="api")


class BaseApiController(http.Controller):
    """
    Base controller for API endpoints with authentication.

    All API endpoints should inherit from this controller to get
    consistent authentication and error handling.

    Authentication uses HMAC-SHA256 signature verification, similar to webhooks:
    - X-Tesote-Signature: HMAC-SHA256 signature of the request
    - X-Tesote-Timestamp: Unix timestamp of the request
    """

    def _get_webhook_config(self):
        """
        Get the webhook configuration for signature verification.

        Returns:
            tesote.webhook.config record or None
        """
        backend = request.env["tesote.backend"].sudo().search([], limit=1)
        if not backend:
            return None

        webhook_config = (
            request.env["tesote.webhook.config"]
            .sudo()
            .search([("backend_id", "=", backend.id)], limit=1)
        )
        return webhook_config

    def _verify_api_key(self):
        """
        Verify the API request signature using the webhook secret key.

        The signature is computed as:
        HMAC-SHA256(secret_key, timestamp + "." + request_path + "." + query_string)

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        headers = request.httprequest.headers
        signature = headers.get("X-Tesote-Signature")
        timestamp = headers.get("X-Tesote-Timestamp")

        if not signature or not timestamp:
            return False, "Missing authentication headers"

        webhook_config = self._get_webhook_config()
        if not webhook_config:
            _logger.error("No webhook configuration found for API authentication")
            return False, "API not configured"

        if not webhook_config.secret_key:
            _logger.error("No secret key configured for API authentication")
            return False, "API not configured"

        try:
            # Construct the signed payload: timestamp.path.query_string
            path = request.httprequest.path
            query_string = request.httprequest.query_string.decode("utf-8")
            signed_payload = f"{timestamp}.{path}.{query_string}"

            # Calculate expected signature
            expected = hmac.new(
                webhook_config.secret_key.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            # Compare signatures securely
            if hmac.compare_digest(expected, signature):
                return True, None
            else:
                _logger.warning("API signature verification failed")
                return False, "Invalid signature"

        except Exception as e:
            _logger.error(f"Error verifying API signature: {e}")
            capture_exception(e)
            return False, "Authentication error"

    def _authenticate_request(self):
        """
        Authenticate the incoming API request.

        Returns:
            tuple: (is_authenticated: bool, error_response: Response or None)
        """
        is_valid, error_message = self._verify_api_key()
        if not is_valid:
            return False, self._json_response({"error": error_message}, status=401)
        return True, None

    def _json_response(self, data, status=200):
        """
        Create a JSON HTTP response.

        Args:
            data: Dictionary to serialize as JSON
            status: HTTP status code

        Returns:
            Odoo HTTP response object
        """
        return request.make_response(
            json.dumps(data, indent=2),
            status=status,
            headers=[("Content-Type", "application/json")],
        )
