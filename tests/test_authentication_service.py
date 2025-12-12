"""
Tests for authentication service (HMAC-SHA256).

TDD approach: Write tests first, then implement.
"""

import hashlib
import hmac
import time
import unittest


class TestAuthenticationService(unittest.TestCase):
    """Test HMAC-SHA256 authentication service."""

    def setUp(self):
        """Set up test fixtures."""
        self.secret_key = "test_secret_key_12345"
        self.timestamp = str(int(time.time()))
        self.path = "/tesote/api/v1/accounting/accounts"
        self.query_string = "limit=100&cursor=0"

    def test_verify_signature_valid(self):
        """Test verification of valid HMAC signature."""
        from services.authentication_service import AuthenticationService

        # Generate valid signature
        signed_payload = f"{self.timestamp}.{self.path}.{self.query_string}"
        signature = hmac.new(
            self.secret_key.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Verify signature
        is_valid, error = AuthenticationService.verify_signature(
            secret_key=self.secret_key,
            signature=signature,
            timestamp=self.timestamp,
            path=self.path,
            query_string=self.query_string,
        )

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_verify_signature_invalid(self):
        """Test verification of invalid HMAC signature."""
        from services.authentication_service import AuthenticationService

        # Generate signature with wrong secret
        wrong_secret = "wrong_secret"
        signed_payload = f"{self.timestamp}.{self.path}.{self.query_string}"
        signature = hmac.new(
            wrong_secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Verify signature (should fail)
        is_valid, error = AuthenticationService.verify_signature(
            secret_key=self.secret_key,
            signature=signature,
            timestamp=self.timestamp,
            path=self.path,
            query_string=self.query_string,
        )

        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn("Invalid signature", error)

    def test_verify_signature_replay_attack(self):
        """Test replay attack prevention (old timestamp)."""
        from services.authentication_service import AuthenticationService

        # Generate signature with old timestamp (10 minutes ago)
        old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
        signed_payload = f"{old_timestamp}.{self.path}.{self.query_string}"
        signature = hmac.new(
            self.secret_key.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Verify signature (should fail due to old timestamp)
        is_valid, error = AuthenticationService.verify_signature(
            secret_key=self.secret_key,
            signature=signature,
            timestamp=old_timestamp,
            path=self.path,
            query_string=self.query_string,
        )

        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn("Timestamp out of tolerance", error)

    def test_verify_signature_invalid_timestamp_format(self):
        """Test invalid timestamp format."""
        from services.authentication_service import AuthenticationService

        invalid_timestamp = "invalid"
        signature = "dummy_signature"

        is_valid, error = AuthenticationService.verify_signature(
            secret_key=self.secret_key,
            signature=signature,
            timestamp=invalid_timestamp,
            path=self.path,
            query_string=self.query_string,
        )

        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn("Invalid timestamp format", error)

    def test_generate_signature(self):
        """Test signature generation."""
        from services.authentication_service import AuthenticationService

        signature = AuthenticationService.generate_signature(
            secret_key=self.secret_key,
            timestamp=self.timestamp,
            path=self.path,
            query_string=self.query_string,
        )

        # Verify it's a valid hex string
        self.assertIsInstance(signature, str)
        self.assertEqual(len(signature), 64)  # SHA256 hex = 64 chars

        # Verify it matches manual calculation
        signed_payload = f"{self.timestamp}.{self.path}.{self.query_string}"
        expected = hmac.new(
            self.secret_key.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        self.assertEqual(signature, expected)

    def test_verify_signature_empty_query_string(self):
        """Test signature verification with empty query string."""
        from services.authentication_service import AuthenticationService

        # Generate signature with empty query string
        signed_payload = f"{self.timestamp}.{self.path}."
        signature = hmac.new(
            self.secret_key.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Verify signature
        is_valid, error = AuthenticationService.verify_signature(
            secret_key=self.secret_key,
            signature=signature,
            timestamp=self.timestamp,
            path=self.path,
            query_string="",
        )

        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_timestamp_tolerance_boundary(self):
        """Test timestamp at tolerance boundary (exactly 5 minutes)."""
        from services.authentication_service import AuthenticationService

        # 5 minutes and 1 second ago (just outside tolerance)
        old_timestamp = str(int(time.time()) - 301)
        signed_payload = f"{old_timestamp}.{self.path}.{self.query_string}"
        signature = hmac.new(
            self.secret_key.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        is_valid, error = AuthenticationService.verify_signature(
            secret_key=self.secret_key,
            signature=signature,
            timestamp=old_timestamp,
            path=self.path,
            query_string=self.query_string,
        )

        # Should fail (outside 5-minute tolerance)
        self.assertFalse(is_valid)
        self.assertIn("Timestamp out of tolerance", error)


if __name__ == "__main__":
    unittest.main()
