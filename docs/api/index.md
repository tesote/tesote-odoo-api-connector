# tesote.com API Documentation

## Overview

Generic, ERP-agnostic REST API for accessing accounting and financial data.

**Base URL:** `http://localhost:8069/tesote/api`

**Version:** v1

**Authentication:** HMAC-SHA256 (see [Authentication](./authentication.md))

## Available APIs

### Accounting

Access chart of accounts, account details, and statistics.

**Endpoints:**
- [Accounting Accounts API](./accounting/accounts.md) - `/v1/accounting/accounts`

**Features:**
- Cursor-based pagination (fast, stateless)
- Search and filtering
- Account types and statistics
- ERP-agnostic (works with Odoo, SAP, etc.)

## Quick Start

**1. Setup Authentication:**

See [Authentication Guide](./authentication.md) for complete setup.

**2. Make Your First Request:**

```python
import requests
import hmac
import hashlib
import time

# Get your secret from webhook config
SECRET_KEY = "your_webhook_secret"

def call_api(path, query_string=""):
    timestamp = str(int(time.time()))
    signed = f"{timestamp}.{path}.{query_string}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        signed.encode(),
        hashlib.sha256
    ).hexdigest()

    return requests.get(
        f"http://localhost:8069{path}?{query_string}",
        headers={
            "X-Tesote-Signature": signature,
            "X-Tesote-Timestamp": timestamp
        }
    )

# List accounts
response = call_api("/tesote/api/v1/accounting/accounts", "limit=10")
data = response.json()

print(f"Retrieved {data['metadata']['count']} accounts")
for account in data['data']:
    print(f"  [{account['code']}] {account['name']}")
```

**3. Explore the APIs:**

- [Accounting Accounts](./accounting/accounts.md) - Chart of accounts, search, statistics

## Common Patterns

### Pagination

All list endpoints use cursor-based pagination:

```python
cursor = None
all_items = []

while True:
    query = f"cursor={cursor}&limit=100" if cursor else "limit=100"
    response = call_api("/tesote/api/v1/accounting/accounts", query)
    data = response.json()

    all_items.extend(data['data'])

    if not data['metadata']['has_more']:
        break

    cursor = data['metadata']['next_cursor']
```

### Error Handling

All endpoints return consistent error format:

```json
{
  "status": "error",
  "error_code": "AUTH001",
  "error": "Invalid signature"
}
```

**Error Codes:**
- `AUTH001` - Authentication failed
- `VALIDATION001` - Invalid parameters
- `NOT_FOUND001` - Resource not found
- `SERVER001` - Internal server error

### Response Format

All successful responses follow:

```json
{
  "status": "success",
  "data": { ... },
  "metadata": { ... },
  "timestamp": "2025-12-12T20:00:00.000000"
}
```

## Testing

**Integration tests:**
```bash
python3 bin/test-api-v1.py
```

**Unit tests:**
```bash
uv run pytest tests/test_authentication_service.py -v
uv run pytest tests/test_odoo_accounting_service.py -v
```

## Architecture

**ERP-Agnostic Design:**
- Controllers are generic (no ERP-specific code)
- Service layer abstracts ERP implementation
- Same API works with Odoo, SAP, NetSuite, etc.

**SOLID Principles:**
- Single Responsibility
- Open/Closed (extend without modifying)
- Dependency Inversion (depend on abstractions)

See [Architecture Guide](../ARCHITECTURE.md) for details.

## Support

- **GitHub Issues**: https://github.com/tesote/tesote-odoo-api-connector/issues
- **Email**: support-odoo@tesote.com
- **Documentation**: This directory

## Changelog

- **v1** (2025-12-12): Initial release
  - Accounting accounts API
  - HMAC-SHA256 authentication
  - Cursor-based pagination
  - Search and filtering
