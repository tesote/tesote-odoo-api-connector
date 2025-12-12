#!/usr/bin/env python3
"""
Integration test for Generic Accounting API v1.

Tests all endpoints at /tesote/api/v1/accounting/accounts with HMAC authentication.
"""

import hashlib
import hmac
import json
import time

import requests

BASE_URL = "http://localhost:8069"


def get_webhook_secret():
    """Get webhook secret key from Odoo."""
    session = requests.Session()

    auth_response = session.post(
        f"{BASE_URL}/web/session/authenticate",
        json={
            "jsonrpc": "2.0",
            "params": {"db": "tesote_dev", "login": "admin", "password": "admin"},
        },
    )

    if not auth_response.json().get("result", {}).get("uid"):
        return None

    config_response = session.post(
        f"{BASE_URL}/web/dataset/call_kw",
        json={
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "tesote.webhook.config",
                "method": "search_read",
                "args": [[]],
                "kwargs": {"fields": ["secret_key"], "limit": 1},
            },
        },
    )

    result = config_response.json().get("result", [])
    return result[0]["secret_key"] if result and result[0].get("secret_key") else None


def call_api(path, method="GET", body=None, query_string="", secret_key=None):
    """Call API with HMAC authentication."""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{path}.{query_string}"
    signature = hmac.new(
        secret_key.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Tesote-Signature": signature,
        "X-Tesote-Timestamp": timestamp,
        "Content-Type": "application/json",
    }

    url = f"{BASE_URL}{path}"
    if query_string:
        url = f"{url}?{query_string}"

    if method == "GET":
        return requests.get(url, headers=headers)
    elif method == "POST":
        return requests.post(url, headers=headers, data=json.dumps(body or {}))


def test_list_accounts(secret_key):
    """Test cursor pagination."""
    print("\n" + "=" * 60)
    print("TEST 1: List accounts with cursor pagination")
    print("=" * 60)

    response = call_api(
        "/tesote/api/v1/accounting/accounts", query_string="limit=5", secret_key=secret_key
    )

    if response.status_code != 200:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False

    data = response.json()
    print(f"✓ Page 1: {data['metadata']['count']} accounts")
    print(f"  Next cursor: {data['metadata']['next_cursor']}")
    print(f"  Has more: {data['metadata']['has_more']}")

    if data["data"]:
        print(f"\nFirst account: [{data['data'][0]['code']}] {data['data'][0]['name']}")

    # Test page 2
    if data["metadata"]["next_cursor"]:
        cursor = data["metadata"]["next_cursor"]
        response2 = call_api(
            "/tesote/api/v1/accounting/accounts",
            query_string=f"cursor={cursor}&limit=5",
            secret_key=secret_key,
        )
        if response2.status_code == 200:
            print(f"✓ Page 2: {response2.json()['metadata']['count']} accounts")

    return True


def test_get_account(secret_key):
    """Test get account by ID."""
    print("\n" + "=" * 60)
    print("TEST 2: Get account by ID")
    print("=" * 60)

    response = call_api("/tesote/api/v1/accounting/accounts/1", secret_key=secret_key)

    if response.status_code == 200:
        data = response.json()
        acc = data.get("data", {})
        print(f"✓ Account {acc.get('id')}: [{acc.get('code')}] {acc.get('name')}")
        return True
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False


def test_search(secret_key):
    """Test search endpoint."""
    print("\n" + "=" * 60)
    print("TEST 3: Search accounts")
    print("=" * 60)

    response = call_api(
        "/tesote/api/v1/accounting/accounts/search",
        method="POST",
        body={"code": "10", "limit": 3},
        secret_key=secret_key,
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {data['metadata']['count']} accounts matching code='10'")
        for acc in data["data"]:
            print(f"  [{acc['code']}] {acc['name']}")
        return True
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False


def test_types(secret_key):
    """Test get types endpoint."""
    print("\n" + "=" * 60)
    print("TEST 4: Get account types")
    print("=" * 60)

    response = call_api("/tesote/api/v1/accounting/accounts/types", secret_key=secret_key)

    if response.status_code == 200:
        data = response.json()
        types = data["data"]
        print(f"✓ Retrieved {len(types)} account types")
        for t in types[:5]:
            print(f"  - {t}")
        return True
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False


def test_stats(secret_key):
    """Test statistics endpoint."""
    print("\n" + "=" * 60)
    print("TEST 5: Get statistics")
    print("=" * 60)

    response = call_api("/tesote/api/v1/accounting/accounts/stats", secret_key=secret_key)

    if response.status_code == 200:
        data = response.json()
        stats = data["data"]
        print("✓ Statistics:")
        print(f"  Total: {stats['total_accounts']}")
        print(f"  Reconcilable: {stats['reconcilable_count']}")
        return True
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Generic Accounting API v1 - Integration Test")
    print("=" * 60)

    secret_key = get_webhook_secret()
    if not secret_key:
        print("\n❌ Cannot run tests - no webhook secret configured")
        return

    print(f"✓ Using secret: {secret_key[:8]}...{secret_key[-4:]}\n")

    tests = [
        ("Cursor Pagination", lambda: test_list_accounts(secret_key)),
        ("Get Account by ID", lambda: test_get_account(secret_key)),
        ("Search Accounts", lambda: test_search(secret_key)),
        ("Get Account Types", lambda: test_types(secret_key)),
        ("Get Statistics", lambda: test_stats(secret_key)),
    ]

    results = [(name, test()) for name, test in tests]

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, success in results:
        print(f"{'✓' if success else '❌'} {name}")

    passed = sum(1 for _, s in results if s)
    print(f"\nPassed: {passed}/{len(results)}")


if __name__ == "__main__":
    main()
