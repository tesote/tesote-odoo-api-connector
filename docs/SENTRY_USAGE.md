# Sentry Error Tracking Integration

This document describes the Sentry error tracking integration for the tesote_connector Odoo module.

## Overview

The module includes automatic error tracking using Sentry.io with the following features:

- **Obfuscated DSN**: DSN is base64-encoded to avoid plain-text exposure in source code
- **Module-specific filtering**: Only captures errors originating from `tesote_connector` code
- **Automatic initialization**: Sentry is initialized when the Odoo module loads
- **Manual capture helpers**: Convenience functions for explicitly capturing exceptions and messages

## Automatic Error Capture

Sentry automatically captures all unhandled exceptions that occur within the `tesote_connector` module. No additional code is required - just install and use the module normally.

### What Gets Captured

- Errors in API communication (`components/adapter.py`)
- Model validation errors (`models/*.py`)
- Webhook processing errors (`components/webhook_processor.py`)
- Sync operation failures

### What Doesn't Get Captured

- Errors from other Odoo modules
- Errors from Odoo core
- Errors from third-party dependencies (unless called from our code)

## HTTP Request/Response Breadcrumbs

The adapter automatically adds detailed breadcrumbs for all HTTP requests and responses to the tesote.com API. This makes debugging API issues much easier by providing a complete audit trail in Sentry.

### What's Captured

For **each HTTP request**, the following information is captured:
- HTTP method (GET, POST, etc.)
- Full URL
- Request headers (with sensitive values redacted)
- Request body (truncated if > 5KB)

For **each HTTP response**, the following information is captured:
- HTTP method and URL
- Status code
- Response headers (with sensitive values redacted)
- Response body (truncated if > 5KB)

For **network errors** (timeout, connection errors):
- Error type and message
- Request details that failed

### Security Features

Sensitive headers are automatically redacted:
- `Authorization: ***REDACTED***`
- `X-API-Key: ***REDACTED***`
- `Cookie: ***REDACTED***`
- `Set-Cookie: ***REDACTED***`

Large payloads (>5KB) are automatically truncated to prevent breadcrumb bloat.

### Example Breadcrumb Data

When viewing an error in Sentry, you'll see breadcrumbs like:

```
Tesote API REQUEST: POST https://api.tesote.com/api/v2/accounts/acc_123/transactions/sync
  method: POST
  url: https://api.tesote.com/api/v2/accounts/acc_123/transactions/sync
  headers:
    Authorization: ***REDACTED***
    Content-Type: application/json
    User-Agent: TesoteOdooConnector/18.0.1.0.0 (API/v2; Odoo/18.0; Python/requests)
  body:
    cursor: "csr_abc123"
    count: 100

Tesote API RESPONSE: POST https://api.tesote.com/api/v2/accounts/acc_123/transactions/sync
  method: POST
  url: https://api.tesote.com/api/v2/accounts/acc_123/transactions/sync
  status_code: 200
  headers:
    Content-Type: application/json
    X-RateLimit-Limit: 200
    X-RateLimit-Remaining: 150
  response:
    added: [...]
    modified: []
    removed: []
    next_cursor: "csr_xyz789"
    has_more: false
```

This provides complete visibility into API interactions when debugging errors.

### Development vs Production Logging

The module includes smart logging that changes based on your environment:

**Development Mode** (when `--dev=all` flag is used or `ODOO_ENV=development`):
- Detailed request bodies logged to console
- Detailed response bodies logged to console
- Rate limit information shown
- Full sync request details displayed
- Sentry breadcrumbs captured (always active)

**Production Mode**:
- Only high-level summaries logged (`API Request: POST /api/v2/...`, `Response status: 200`)
- Sync statistics logged (`Sync result: 5 added, 2 modified, 0 removed`)
- Error status codes without full body (body still captured in Sentry)
- Sentry breadcrumbs captured (always active)

**How to enable dev mode logging:**
```bash
# Docker (already configured)
./bin/docker-dev up  # Uses --dev=all in docker-compose.yml

# Manual Odoo
odoo --dev=all -d your_database

# Environment variable (fallback)
export ODOO_ENV=development
odoo -d your_database
```

**Why this matters:**
- In development: Full visibility for debugging
- In production: Clean logs, sensitive data protected, full details in Sentry
- Sentry always captures everything regardless of environment

## Manual Error Capture

For specific error scenarios where you want to explicitly send an error to Sentry:

```python
from odoo.addons.tesote_connector.utils.sentry_config import capture_exception

try:
    # Some risky operation
    result = api_call()
except Exception as e:
    # Log locally
    _logger.error(f"API call failed: {e}")

    # Also send to Sentry with additional context
    capture_exception(
        e,
        level="error",
        tags={
            "operation": "api_sync",
            "account_id": account.id,
        }
    )
    raise
```

## Manual Message Capture

To send informational messages or warnings to Sentry (useful for tracking important events):

```python
from odoo.addons.tesote_connector.utils.sentry_config import capture_message

# After a successful but noteworthy operation
capture_message(
    "Large sync completed successfully",
    level="info",
    tags={
        "accounts_synced": 150,
        "transactions_added": 5000,
    }
)
```

## Configuration

### DSN Obfuscation

The Sentry DSN is stored as a base64-encoded string in `utils/sentry_config.py`:

```python
_OBFUSCATED_DSN = "aHR0cHM6Ly8xMDNjNz..."
```

**Note**: This provides obfuscation, not security. The DSN can be decoded by anyone with access to the source code. However, Sentry DSNs are meant to be public-facing (they're used in client-side JavaScript), so this level of obfuscation is acceptable.

### Environment Configuration

You can customize the Sentry environment by editing `utils/sentry_config.py`:

```python
environment="production",  # Change to "staging" or "development"
```

### Changing the DSN

To update the DSN:

1. Get your new DSN from Sentry.io
2. Encode it to base64:
   ```python
   import base64
   dsn = "https://your-new-dsn@sentry.io/project"
   encoded = base64.b64encode(dsn.encode()).decode()
   print(encoded)
   ```
3. Update `_OBFUSCATED_DSN` in `utils/sentry_config.py`

## Event Filtering

The module uses a `before_send` hook to filter events. Only events with stack frames containing `tesote_connector` or `tesote-odoo-api-connector` in their file paths are sent to Sentry.

### Filter Logic

```python
def _should_capture_event(event, hint):
    # Checks exception traceback for tesote_connector frames
    # Returns event if found, None to drop
```

This ensures that:
- You only pay for errors from your code
- Sentry doesn't get flooded with unrelated errors
- Error reports are focused and actionable

## Testing

The integration includes comprehensive tests in `tests/test_sentry_config.py`:

```bash
# Run Sentry tests only
uv run pytest tests/test_sentry_config.py -v

# Run all tests (including Sentry)
uv run pytest
```

## Sentry Dashboard

All captured errors appear in your Sentry dashboard with:

- **Environment**: production/staging/development
- **Release**: tesote_connector@18.0.1.0.0
- **Tags**: module=tesote_connector, odoo_version=18.0
- **Context**: Request data, user info (if `send_default_pii=True`)

## Disabling Sentry

If you need to disable Sentry temporarily:

1. **For testing**: Tests automatically mock Sentry - no special configuration needed
2. **For production**: Remove or comment out the initialization in `__init__.py`
3. **Uninstall package**: Remove `sentry-sdk` from dependencies (module will still work)

## Performance Impact

Sentry is configured with:

- **Performance monitoring disabled**: `traces_sample_rate=0.0`
- **Minimal overhead**: Only active when exceptions occur
- **Async sending**: Doesn't block request handling

The performance impact should be negligible (<1ms per request in normal operation).

## Security Considerations

1. **DSN Exposure**: The DSN is obfuscated but not encrypted. This is acceptable since Sentry DSNs are designed to be public.
2. **PII Data**: `send_default_pii=True` includes request headers and user data. Review Sentry's data handling policies for compliance.
3. **Error Content**: Be careful not to log sensitive data (passwords, API keys) in error messages.

## Troubleshooting

### Sentry not capturing errors

1. Check that `sentry-sdk` is installed: `pip list | grep sentry`
2. Check Odoo logs for initialization message: "Sentry SDK initialized successfully"
3. Verify errors are from `tesote_connector` code (filtering may be dropping them)
4. Check Sentry.io dashboard for rate limits or quota issues

### Too many errors being captured

1. Review the `_should_capture_event` filter logic
2. Add additional filtering conditions as needed
3. Adjust Sentry's rate limiting in the dashboard

### DSN decode error

1. Verify `_OBFUSCATED_DSN` is valid base64
2. Check for line breaks or extra characters in the string
3. Re-encode the DSN following the instructions above

## Additional Resources

- [Sentry Python Documentation](https://docs.sentry.io/platforms/python/)
- [Sentry Error Filtering](https://docs.sentry.io/platforms/python/configuration/filtering/)
- [Sentry Data Management](https://docs.sentry.io/platforms/python/data-management/)
