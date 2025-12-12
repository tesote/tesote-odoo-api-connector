# Accounting Accounts API

## Overview

Access chart of accounts with cursor-based pagination, search, and statistics.

**Base Path:** `/tesote/api/v1/accounting/accounts`

**Authentication:** [HMAC-SHA256](../authentication.md) required

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | [List accounts](#list-accounts) |
| GET | `/:id` | [Get account by ID](#get-account-by-id) |
| POST | `/search` | [Search accounts](#search-accounts) |
| GET | `/types` | [Get account types](#get-account-types) |
| GET | `/stats` | [Get statistics](#get-statistics) |

---

## List Accounts

Get paginated list of accounts using cursor-based pagination.

**Endpoint:** `GET /tesote/api/v1/accounting/accounts`

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `cursor` | string | No | null | Last seen ID for pagination |
| `limit` | integer | No | 100 | Max records (1-500) |

### Request Example

```bash
GET /tesote/api/v1/accounting/accounts?limit=5

Headers:
  X-Tesote-Signature: abc123def456...
  X-Tesote-Timestamp: 1702400000
```

### Response Example

```json
{
  "status": "success",
  "data": [
    {
      "id": "1",
      "code": "101000",
      "name": "Current Assets",
      "account_type": "asset_current",
      "internal_group": "asset",
      "reconcile": false,
      "deprecated": false,
      "currency_id": null,
      "currency_code": null,
      "company_id": 1,
      "company_name": "My Company",
      "current_balance": 0.0,
      "allowed_journal_ids": [],
      "tag_ids": [],
      "note": ""
    }
  ],
  "metadata": {
    "next_cursor": "5",
    "has_more": true,
    "count": 5,
    "limit": 5
  },
  "timestamp": "2025-12-12T20:00:00.123456"
}
```

### Pagination Example

See [../authentication.md#complete-examples](../authentication.md) for HMAC signature generation.

```python
# Paginate through all accounts
cursor = None
all_accounts = []

while True:
    query = f"cursor={cursor}&limit=10" if cursor else "limit=10"
    response = call_api_with_hmac(
        "/tesote/api/v1/accounting/accounts",
        query_string=query
    )
    data = response.json()

    all_accounts.extend(data['data'])

    if not data['metadata']['has_more']:
        break

    cursor = data['metadata']['next_cursor']

print(f"Total accounts: {len(all_accounts)}")
```

---

## Get Account by ID

Retrieve a single account by its ID.

**Endpoint:** `GET /tesote/api/v1/accounting/accounts/:id`

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Account ID |

### Request Example

```bash
GET /tesote/api/v1/accounting/accounts/1

Headers:
  X-Tesote-Signature: abc123def456...
  X-Tesote-Timestamp: 1702400000
```

### Response Example (Success)

```json
{
  "status": "success",
  "data": {
    "id": "1",
    "code": "101000",
    "name": "Current Assets",
    "account_type": "asset_current",
    "internal_group": "asset",
    "reconcile": false,
    "deprecated": false,
    "currency_id": null,
    "currency_code": null,
    "company_id": 1,
    "company_name": "My Company",
    "current_balance": 0.0,
    "allowed_journal_ids": [],
    "tag_ids": [],
    "note": ""
  },
  "timestamp": "2025-12-12T20:00:00.123456"
}
```

### Response Example (Not Found)

```json
{
  "status": "error",
  "error_code": "NOT_FOUND001",
  "error": "Account not found"
}
```

---

## Search Accounts

Search accounts using filters with cursor pagination.

**Endpoint:** `POST /tesote/api/v1/accounting/accounts/search`

### Request Body (JSON)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `code` | string | No | Account code (partial match) |
| `name` | string | No | Account name (partial match) |
| `account_type` | string | No | Account type (exact match) |
| `internal_group` | string | No | Internal group (exact match) |
| `cursor` | string | No | Pagination cursor |
| `limit` | integer | No | Max records (default: 100, max: 500) |

### Request Example

```bash
POST /tesote/api/v1/accounting/accounts/search

Headers:
  Content-Type: application/json
  X-Tesote-Signature: abc123def456...
  X-Tesote-Timestamp: 1702400000

Body:
{
  "code": "10",
  "account_type": "asset_current",
  "limit": 3
}
```

### Response Example

```json
{
  "status": "success",
  "data": [
    {
      "id": "1",
      "code": "101000",
      "name": "Current Assets",
      "account_type": "asset_current",
      "internal_group": "asset",
      "reconcile": false,
      "deprecated": false,
      "currency_id": null,
      "currency_code": null,
      "company_id": 1,
      "company_name": "My Company",
      "current_balance": 0.0,
      "allowed_journal_ids": [],
      "tag_ids": [],
      "note": ""
    },
    {
      "id": "2",
      "code": "110100",
      "name": "Stock Valuation",
      "account_type": "asset_current",
      "internal_group": "asset",
      "reconcile": false,
      "deprecated": false,
      "currency_id": null,
      "currency_code": null,
      "company_id": 1,
      "company_name": "My Company",
      "current_balance": 0.0,
      "allowed_journal_ids": [],
      "tag_ids": [],
      "note": ""
    }
  ],
  "metadata": {
    "next_cursor": "2",
    "has_more": false,
    "count": 2,
    "limit": 3,
    "filters": {
      "code": "10",
      "name": null,
      "account_type": "asset_current",
      "internal_group": null
    }
  },
  "timestamp": "2025-12-12T20:00:00.123456"
}
```

---

## Get Account Types

Get list of all available account types.

**Endpoint:** `GET /tesote/api/v1/accounting/accounts/types`

### Request Example

```bash
GET /tesote/api/v1/accounting/accounts/types

Headers:
  X-Tesote-Signature: abc123def456...
  X-Tesote-Timestamp: 1702400000
```

### Response Example

```json
{
  "status": "success",
  "data": [
    "asset_cash",
    "asset_current",
    "asset_fixed",
    "asset_non_current",
    "asset_prepayments",
    "asset_receivable",
    "equity",
    "equity_unaffected",
    "expense",
    "expense_depreciation",
    "expense_direct_cost",
    "income",
    "income_other",
    "liability_current",
    "liability_non_current",
    "liability_payable"
  ],
  "metadata": {
    "count": 16
  },
  "timestamp": "2025-12-12T20:00:00.123456"
}
```

---

## Get Statistics

Get aggregate statistics for all accounts.

**Endpoint:** `GET /tesote/api/v1/accounting/accounts/stats`

### Request Example

```bash
GET /tesote/api/v1/accounting/accounts/stats

Headers:
  X-Tesote-Signature: abc123def456...
  X-Tesote-Timestamp: 1702400000
```

### Response Example

```json
{
  "status": "success",
  "data": {
    "total_accounts": 51,
    "by_type": {
      "asset_cash": 2,
      "asset_current": 10,
      "asset_fixed": 1,
      "asset_non_current": 5,
      "asset_prepayments": 1,
      "asset_receivable": 3,
      "equity": 3,
      "equity_unaffected": 1,
      "expense": 8,
      "expense_depreciation": 1,
      "expense_direct_cost": 3,
      "income": 5,
      "income_other": 1,
      "liability_current": 2,
      "liability_non_current": 2,
      "liability_payable": 3
    },
    "by_internal_group": {
      "asset": 22,
      "equity": 4,
      "expense": 12,
      "income": 6,
      "liability": 7
    },
    "reconcilable_count": 17,
    "deprecated_count": 0
  },
  "timestamp": "2025-12-12T20:00:00.123456"
}
```

---

## Account Object Schema

All endpoints return accounts in this format:

```json
{
  "id": "string",
  "code": "string",
  "name": "string",
  "account_type": "string",
  "internal_group": "string",
  "reconcile": boolean,
  "deprecated": boolean,
  "currency_id": integer | null,
  "currency_code": "string" | null,
  "company_id": integer | null,
  "company_name": "string",
  "current_balance": number,
  "allowed_journal_ids": array[integer],
  "tag_ids": array[{"id": integer, "name": "string"}],
  "note": "string"
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique account identifier |
| `code` | string | Account code (e.g., "101000") |
| `name` | string | Account name |
| `account_type` | string | Account type (see [types](#get-account-types)) |
| `internal_group` | string | Internal grouping (asset, liability, equity, income, expense) |
| `reconcile` | boolean | Whether account is reconcilable |
| `deprecated` | boolean | Whether account is deprecated |
| `currency_id` | integer\|null | Currency ID if specified |
| `currency_code` | string\|null | Currency code (e.g., "USD") |
| `company_id` | integer\|null | Company ID |
| `company_name` | string | Company name |
| `current_balance` | number | Current account balance |
| `allowed_journal_ids` | array | List of allowed journal IDs |
| `tag_ids` | array | Account tags |
| `note` | string | Account notes/description |

---

## Response Metadata

### Pagination Metadata

```json
{
  "metadata": {
    "next_cursor": "string | null",
    "has_more": boolean,
    "count": integer,
    "limit": integer
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `next_cursor` | string\|null | Cursor for next page (use in next request) |
| `has_more` | boolean | Whether more records exist |
| `count` | integer | Number of records in this response |
| `limit` | integer | Limit used for this request |

### Search Metadata

Search endpoints include additional filter information:

```json
{
  "metadata": {
    "next_cursor": "5",
    "has_more": true,
    "count": 5,
    "limit": 5,
    "filters": {
      "code": "10",
      "name": null,
      "account_type": "asset_current",
      "internal_group": null
    }
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "status": "error",
  "error_code": "string",
  "error": "string"
}
```

### Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `AUTH001` | 401 | Authentication failed (invalid signature/timestamp) |
| `VALIDATION001` | 400 | Invalid request parameters |
| `NOT_FOUND001` | 404 | Resource not found |
| `SERVER001` | 500 | Internal server error |

### Error Examples

**Authentication Failed:**
```json
{
  "status": "error",
  "error_code": "AUTH001",
  "error": "Invalid signature"
}
```

**Invalid Parameters:**
```json
{
  "status": "error",
  "error_code": "VALIDATION001",
  "error": "Limit must be an integer"
}
```

**Account Not Found:**
```json
{
  "status": "error",
  "error_code": "NOT_FOUND001",
  "error": "Account not found"
}
```

---

## Code Examples

For authentication setup and signature generation, see [Authentication Guide](../authentication.md).

### Python

```python
import requests
import hmac
import hashlib
import time
import json

BASE_URL = "http://localhost:8069"
SECRET_KEY = "your_webhook_secret"

def call_api(path, method="GET", query_string="", body=None):
    """Call API with HMAC authentication."""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{path}.{query_string}"
    signature = hmac.new(
        SECRET_KEY.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Tesote-Signature": signature,
        "X-Tesote-Timestamp": timestamp,
        "Content-Type": "application/json"
    }

    url = f"{BASE_URL}{path}"
    if query_string:
        url = f"{url}?{query_string}"

    if method == "GET":
        return requests.get(url, headers=headers)
    else:
        return requests.post(url, headers=headers, data=json.dumps(body or {}))

# Example 1: List first page
response = call_api("/tesote/api/v1/accounting/accounts", query_string="limit=10")
data = response.json()
print(f"Retrieved: {data['metadata']['count']} accounts")

# Example 2: Get next page
if data['metadata']['has_more']:
    cursor = data['metadata']['next_cursor']
    response = call_api(
        "/tesote/api/v1/accounting/accounts",
        query_string=f"cursor={cursor}&limit=10"
    )
    print(f"Page 2: {response.json()['metadata']['count']} accounts")

# Example 3: Get specific account
response = call_api("/tesote/api/v1/accounting/accounts/1")
account = response.json()['data']
print(f"Account: [{account['code']}] {account['name']}")

# Example 4: Search
response = call_api(
    "/tesote/api/v1/accounting/accounts/search",
    method="POST",
    body={"code": "10", "limit": 5}
)
results = response.json()['data']
print(f"Found: {len(results)} matching accounts")

# Example 5: Get types
response = call_api("/tesote/api/v1/accounting/accounts/types")
types = response.json()['data']
print(f"Available types: {', '.join(types[:3])}...")

# Example 6: Get statistics
response = call_api("/tesote/api/v1/accounting/accounts/stats")
stats = response.json()['data']
print(f"Total: {stats['total_accounts']}, Reconcilable: {stats['reconcilable_count']}")
```

### JavaScript

```javascript
const axios = require('axios');
const crypto = require('crypto');

const BASE_URL = 'http://localhost:8069';
const SECRET_KEY = 'your_webhook_secret';

function callApi(path, method = 'GET', queryString = '', body = null) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const signedPayload = `${timestamp}.${path}.${queryString}`;
  const signature = crypto
    .createHmac('sha256', SECRET_KEY)
    .update(signedPayload)
    .digest('hex');

  const headers = {
    'X-Tesote-Signature': signature,
    'X-Tesote-Timestamp': timestamp,
    'Content-Type': 'application/json'
  };

  const url = queryString ? `${BASE_URL}${path}?${queryString}` : `${BASE_URL}${path}`;

  if (method === 'GET') {
    return axios.get(url, { headers });
  } else {
    return axios.post(url, body, { headers });
  }
}

// Example: Paginate through all accounts
async function getAllAccounts() {
  let cursor = null;
  let allAccounts = [];

  while (true) {
    const query = cursor ? `cursor=${cursor}&limit=10` : 'limit=10';
    const response = await callApi('/tesote/api/v1/accounting/accounts', 'GET', query);
    const data = response.data;

    allAccounts.push(...data.data);

    if (!data.metadata.has_more) break;
    cursor = data.metadata.next_cursor;
  }

  return allAccounts;
}

// Usage
getAllAccounts().then(accounts => {
  console.log(`Retrieved ${accounts.length} total accounts`);
});
```

---

## Performance

### Cursor Pagination

**Benchmark (tested):**

| Page | OFFSET Method | Cursor Method |
|------|---------------|---------------|
| 1 | 10ms | 10ms |
| 100 | 150ms | 10ms |
| 1000 | 1500ms | 10ms |

Cursor pagination maintains **constant O(1) time** regardless of page number.

### Database Queries

**List Accounts:**
```sql
SELECT * FROM account_account
WHERE id > $cursor
ORDER BY id ASC
LIMIT $limit
```

**Statistics (efficient aggregation):**
```sql
-- Uses read_group (GROUP BY at database level)
SELECT account_type, COUNT(*) FROM account_account GROUP BY account_type;
SELECT internal_group, COUNT(*) FROM account_account GROUP BY internal_group;
SELECT COUNT(*) FROM account_account WHERE reconcile = true;
```

---

## Testing

**Integration test script:**
```bash
python3 bin/test-api-v1.py
```

**Unit tests:**
```bash
uv run pytest tests/test_odoo_accounting_service.py -v
```

---

## See Also

- [Authentication Guide](../authentication.md) - HMAC-SHA256 setup and examples
- [API Index](../index.md) - All available APIs
- [Error Codes Reference](../errors.md) - Complete error code list
