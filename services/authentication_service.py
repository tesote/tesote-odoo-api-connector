"""
Authentication service for HMAC-SHA256 signature verification.

This service is ERP-agnostic - no Odoo dependencies.
Can be used with any framework (Odoo, SAP, Django, Flask, etc.).

Based on webhook authentication pattern from:
- models/tesote_webhook_config.py:180-210
"""

import hashlib
import hmac
import time


class AuthenticationService:
    """HMAC-SHA256 authentication service (ERP-agnostic)."""

    # Timestamp tolerance: 5 minutes (300 seconds)
    # Prevents replay attacks while allowing for clock skew
    TIMESTAMP_TOLERANCE = 300

    @staticmethod
    def verify_signature(
        secret_key: str, signature: str, timestamp: str, path: str, query_string: str = ""
    ) -> tuple[bool, str | None]:
        """
        Verify HMAC-SHA256 signature.

        This follows the same pattern as webhook signature verification.
        The signed payload format is: "{timestamp}.{path}.{query_string}"

        Args:
            secret_key: API secret key (shared secret)
            signature: Client-provided signature (hex-encoded)
            timestamp: Request timestamp (Unix epoch as string)
            path: Request path (e.g., /tesote/api/v1/accounting/accounts)
            query_string: URL query string (e.g., limit=100&cursor=0)

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if signature is valid
            - error_message: None if valid, error description if invalid

        Example:
            >>> is_valid, error = AuthenticationService.verify_signature(
            ...     secret_key="my_secret",
            ...     signature="abc123...",
            ...     timestamp="1702400000",
            ...     path="/tesote/api/v1/accounting/accounts",
            ...     query_string="limit=100"
            ... )
        """
        # Step 1: Validate timestamp (prevent replay attacks)
        try:
            ts = int(timestamp)
            now = int(time.time())

            # Check if timestamp is within tolerance (5 minutes)
            if abs(now - ts) > AuthenticationService.TIMESTAMP_TOLERANCE:
                return False, "Timestamp out of tolerance (replay attack?)"

        except (ValueError, TypeError):
            return False, "Invalid timestamp format"

        # Step 2: Reconstruct signed payload
        # Format: "{timestamp}.{path}.{query_string}"
        # This matches webhook pattern from webhook_config.py:193
        signed_payload = f"{timestamp}.{path}.{query_string}"

        # Step 3: Compute expected signature
        expected_signature = hmac.new(
            secret_key.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Step 4: Constant-time comparison (prevents timing attacks)
        # Using hmac.compare_digest for security
        if not hmac.compare_digest(signature, expected_signature):
            return False, "Invalid signature"

        # Signature is valid
        return True, None

    @staticmethod
    def generate_signature(
        secret_key: str, timestamp: str, path: str, query_string: str = ""
    ) -> str:
        """
        Generate HMAC-SHA256 signature.

        This is used for testing and client-side signature generation.

        Args:
            secret_key: API secret key
            timestamp: Request timestamp (Unix epoch as string)
            path: Request path
            query_string: URL query string

        Returns:
            HMAC-SHA256 signature (hex-encoded string)

        Example:
            >>> signature = AuthenticationService.generate_signature(
            ...     secret_key="my_secret",
            ...     timestamp="1702400000",
            ...     path="/tesote/api/v1/accounting/accounts",
            ...     query_string="limit=100"
            ... )
            >>> print(signature)
            'abc123def456...'  # 64-character hex string
        """
        # Construct signed payload
        signed_payload = f"{timestamp}.{path}.{query_string}"

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            secret_key.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return signature
