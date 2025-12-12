"""
Base API controller with HMAC-SHA256 authentication.

All API controllers should inherit from this to get consistent
authentication and response handling.
"""

import json

from odoo import _, http
from odoo.http import request

try:
    from ...services import AuthenticationService
    from ...utils.colored_logger import get_logger
except ImportError:
    from services import AuthenticationService
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="api")


class BaseApiController(http.Controller):
    """
    Base controller for API endpoints with HMAC authentication.

    Authentication uses webhook config secret key for HMAC-SHA256 verification.
    All API endpoints inherit from this controller.

    Headers required:
    - X-Tesote-Signature: HMAC-SHA256 signature
    - X-Tesote-Timestamp: Unix timestamp
    """

    def _get_webhook_config(self):
        """
        Get webhook configuration for authentication.

        Reuses webhook config infrastructure for API authentication.

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

    def _verify_authentication(self):
        """
        Verify HMAC-SHA256 authentication.

        Uses AuthenticationService for signature verification.
        Reuses webhook secret key for API authentication.

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        headers = request.httprequest.headers
        signature = headers.get("X-Tesote-Signature")
        timestamp = headers.get("X-Tesote-Timestamp")

        if not signature or not timestamp:
            return False, _("Missing authentication headers")

        # Get webhook config for secret key
        webhook_config = self._get_webhook_config()
        if not webhook_config or not webhook_config.secret_key:
            _logger.error("No webhook config or secret key found for API auth")
            return False, _("API not configured")

        # Use authentication service to verify signature
        path = request.httprequest.path
        query_string = request.httprequest.query_string.decode("utf-8")

        is_valid, error = AuthenticationService.verify_signature(
            secret_key=webhook_config.secret_key,
            signature=signature,
            timestamp=timestamp,
            path=path,
            query_string=query_string,
        )

        if not is_valid:
            _logger.warning(f"API authentication failed: {error}")

        return is_valid, error

    def _authenticate_request(self):
        """
        Authenticate incoming API request.

        Returns:
            tuple: (is_authenticated: bool, error_response: Response or None)
        """
        is_valid, error_message = self._verify_authentication()
        if not is_valid:
            return False, self._json_response(
                {"status": "error", "error_code": "AUTH001", "error": error_message}, status=401
            )
        return True, None

    def _json_response(self, data, status=200):
        """
        Create JSON HTTP response.

        Args:
            data: Dictionary to serialize as JSON
            status: HTTP status code

        Returns:
            Odoo HTTP response object
        """
        return request.make_response(
            json.dumps(data, indent=2),
            status=status,
            headers=[("Content-Type", "application/json; charset=utf-8")],
        )

    def _validate_limit(self, limit, default=100, max_limit=500):
        """
        Validate and clamp limit parameter.

        Args:
            limit: Limit value (can be str, int, or None)
            default: Default limit if None
            max_limit: Maximum allowed limit

        Returns:
            int: Validated limit (clamped between 1 and max_limit)

        Raises:
            ValueError: If limit is not a valid integer
        """
        try:
            if limit is None:
                return default

            limit_int = int(limit)
            return max(1, min(limit_int, max_limit))

        except (ValueError, TypeError) as e:
            raise ValueError(_("Limit must be an integer")) from e
