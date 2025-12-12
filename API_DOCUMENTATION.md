# Accounting Accounts API Documentation

## Overview

This API provides RESTful endpoints for accessing Odoo accounting accounts data. All endpoints return JSON responses and require authentication.

## Base URL

```
http://localhost:8069
```

## Authentication

All API endpoints require Odoo user authentication. You must first authenticate using Odoo's session API:

```bash
POST /web/session/authenticate
```

**Request Body:**
```json
{
  "jsonrpc": "2.0",
  "params": {
    "db": "tesote_dev",
    "login": "admin",
    "password": "admin"
  }
}
```

The session cookie will be stored and used for subsequent requests.

## API Endpoints

### 1. Get All Accounts

Retrieve a paginated list of accounting accounts.

**Endpoint:** `POST /api/v1/accounts`

**Method:** JSON-RPC

**Parameters:**
- `limit` (integer, optional): Maximum number of records to return. Default: 100
- `offset` (integer, optional): Number of records to skip. Default: 0
- `domain` (array, optional): Odoo domain filter

**Example Request:**
```bash
curl -X POST http://localhost:8069/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "limit": 10,
      "offset": 0
    }
  }'
```

**Example Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
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
      "allowed_journal_ids": [1, 2, 3],
      "tag_ids": [],
      "note": ""
    }
  ],
  "metadata": {
    "total": 51,
    "limit": 10,
    "offset": 0,
    "count": 10
  },
  "timestamp": "2025-12-12T18:20:00.123456"
}
```

### 2. Get Account by ID

Retrieve a single accounting account by its ID.

**Endpoint:** `POST /api/v1/accounts/<account_id>`

**Method:** JSON-RPC

**Parameters:**
- `account_id` (integer, required): The ID of the account to retrieve

**Example Request:**
```bash
curl -X POST http://localhost:8069/api/v1/accounts/1 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {}
  }'
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "id": 1,
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
    "allowed_journal_ids": [1, 2, 3],
    "tag_ids": [],
    "note": ""
  },
  "timestamp": "2025-12-12T18:20:00.123456"
}
```

### 3. Search Accounts

Search for accounts using various filters.

**Endpoint:** `POST /api/v1/accounts/search`

**Method:** JSON-RPC

**Parameters:**
- `code` (string, optional): Filter by account code (partial match, case-insensitive)
- `name` (string, optional): Filter by account name (partial match, case-insensitive)
- `account_type` (string, optional): Filter by exact account type
- `limit` (integer, optional): Maximum number of records to return. Default: 100
- `offset` (integer, optional): Number of records to skip. Default: 0

**Example Request:**
```bash
curl -X POST http://localhost:8069/api/v1/accounts/search \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "code": "10",
      "limit": 5
    }
  }'
```

**Example Response:**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
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
      "allowed_journal_ids": [1, 2, 3],
      "tag_ids": [],
      "note": ""
    }
  ],
  "metadata": {
    "total": 15,
    "limit": 5,
    "offset": 0,
    "count": 5,
    "filters": {
      "code": "10",
      "name": null,
      "account_type": null
    }
  },
  "timestamp": "2025-12-12T18:20:00.123456"
}
```

### 4. Get Account Types

Retrieve a list of all available account types.

**Endpoint:** `POST /api/v1/accounts/types`

**Method:** JSON-RPC

**Example Request:**
```bash
curl -X POST http://localhost:8069/api/v1/accounts/types \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {}
  }'
```

**Example Response:**
```json
{
  "status": "success",
  "data": [
    "asset_cash",
    "asset_current",
    "asset_non_current",
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
    "count": 14
  },
  "timestamp": "2025-12-12T18:20:00.123456"
}
```

### 5. Get Account Statistics

Retrieve statistical information about accounting accounts.

**Endpoint:** `POST /api/v1/accounts/stats`

**Method:** JSON-RPC

**Example Request:**
```bash
curl -X POST http://localhost:8069/api/v1/accounts/stats \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {}
  }'
```

**Example Response:**
```json
{
  "status": "success",
  "data": {
    "total_accounts": 51,
    "reconcilable_count": 8,
    "deprecated_count": 0,
    "by_type": {
      "asset_cash": 2,
      "asset_current": 15,
      "asset_non_current": 5,
      "asset_receivable": 3,
      "equity": 4,
      "expense": 12,
      "income": 6,
      "liability_payable": 2,
      "liability_current": 2
    },
    "by_internal_group": {
      "asset": 25,
      "equity": 4,
      "expense": 12,
      "income": 6,
      "liability": 4
    }
  },
  "timestamp": "2025-12-12T18:20:00.123456"
}
```

## Response Format

All API endpoints return responses in the following format:

### Success Response
```json
{
  "status": "success",
  "data": { ... },
  "metadata": { ... },
  "timestamp": "2025-12-12T18:20:00.123456"
}
```

### Error Response
```json
{
  "status": "error",
  "error": "Error message",
  "timestamp": "2025-12-12T18:20:00.123456"
}
```

## Account Data Structure

Each account object contains the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique account identifier |
| `code` | string | Account code |
| `name` | string | Account name |
| `account_type` | string | Account type (e.g., asset_current, liability_payable) |
| `internal_group` | string | Internal grouping (asset, liability, equity, income, expense) |
| `reconcile` | boolean | Whether the account is reconcilable |
| `deprecated` | boolean | Whether the account is deprecated |
| `currency_id` | integer or null | Currency ID if specified |
| `currency_code` | string or null | Currency code if specified |
| `company_id` | integer | Company ID |
| `company_name` | string | Company name |
| `current_balance` | float | Current account balance |
| `allowed_journal_ids` | array[integer] | List of allowed journal IDs |
| `tag_ids` | array[object] | List of account tags |
| `note` | string | Account notes |

## Testing

Use the provided test script to verify the API endpoints:

```bash
python3 bin/test-accounts-api.py
```

Or test individual endpoints using curl:

```bash
# First, authenticate and save session cookie
curl -c cookies.txt -X POST http://localhost:8069/web/session/authenticate \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "params": {
      "db": "tesote_dev",
      "login": "admin",
      "password": "admin"
    }
  }'

# Then use the cookie for API requests
curl -b cookies.txt -X POST http://localhost:8069/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "limit": 10
    }
  }'
```

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required or failed
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a descriptive error message in the `error` field.

## Rate Limiting

Currently, there are no rate limits enforced. This may change in production deployments.

## Versioning

The current API version is `v1`. The version is included in the endpoint path (`/api/v1/...`).

## Support

For issues or questions, please refer to the project repository:
- GitHub: https://github.com/tesote/tesote-odoo-api-connector
- Email: support-odoo@tesote.com
