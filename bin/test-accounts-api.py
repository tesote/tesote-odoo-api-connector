#!/usr/bin/env python3
"""
Test script for the accounting accounts API.

This script demonstrates how to use the accounting accounts API endpoints.
"""

import requests

# API Configuration
BASE_URL = "http://localhost:8069"
DB_NAME = "tesote_dev"
USERNAME = "admin"
PASSWORD = "admin"

# Create a session
session = requests.Session()


def login():
    """Authenticate and get session cookie."""
    print("Logging in...")
    response = session.post(
        f"{BASE_URL}/web/session/authenticate",
        json={
            "jsonrpc": "2.0",
            "params": {
                "db": DB_NAME,
                "login": USERNAME,
                "password": PASSWORD,
            },
        },
    )
    result = response.json()
    if result.get("result") and result["result"].get("uid"):
        print(f"✓ Logged in as {USERNAME} (UID: {result['result']['uid']})")
        return True
    else:
        print(f"✗ Login failed: {result}")
        return False


def call_api(endpoint, params=None):
    """Call an API endpoint."""
    url = f"{BASE_URL}{endpoint}"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": params or {},
    }

    response = session.post(url, json=payload)
    return response.json()


def test_get_accounts():
    """Test GET /api/v1/accounts endpoint."""
    print("\n" + "=" * 60)
    print("TEST: Get all accounts (limit 10)")
    print("=" * 60)

    result = call_api("/api/v1/accounts", {"limit": 10, "offset": 0})

    if "result" in result:
        data = result["result"]
        print(f"Status: {data.get('status')}")
        print(f"Total accounts: {data.get('metadata', {}).get('total')}")
        print(f"Returned: {data.get('metadata', {}).get('count')}")
        print("\nFirst 5 accounts:")
        for acc in data.get("data", [])[:5]:
            print(f"  [{acc['code']}] {acc['name']} - {acc['account_type']}")
        return True
    else:
        print(f"Error: {result}")
        return False


def test_get_account_by_id():
    """Test GET /api/v1/accounts/<id> endpoint."""
    print("\n" + "=" * 60)
    print("TEST: Get account by ID")
    print("=" * 60)

    # First get an account ID
    accounts_result = call_api("/api/v1/accounts", {"limit": 1})
    if "result" in accounts_result and accounts_result["result"].get("data"):
        account_id = accounts_result["result"]["data"][0]["id"]

        result = call_api(f"/api/v1/accounts/{account_id}")

        if "result" in result:
            data = result["result"]
            if data.get("status") == "success":
                acc = data["data"]
                print(f"Account ID: {acc['id']}")
                print(f"Code: {acc['code']}")
                print(f"Name: {acc['name']}")
                print(f"Type: {acc['account_type']}")
                print(f"Balance: {acc['current_balance']}")
                return True
        print(f"Error: {result}")
        return False
    else:
        print("No accounts available for testing")
        return False


def test_search_accounts():
    """Test POST /api/v1/accounts/search endpoint."""
    print("\n" + "=" * 60)
    print("TEST: Search accounts (code contains '10')")
    print("=" * 60)

    result = call_api("/api/v1/accounts/search", {"code": "10", "limit": 5})

    if "result" in result:
        data = result["result"]
        print(f"Status: {data.get('status')}")
        print(f"Found: {data.get('metadata', {}).get('total')} accounts")
        print(f"Returned: {data.get('metadata', {}).get('count')}")
        print("\nAccounts:")
        for acc in data.get("data", []):
            print(f"  [{acc['code']}] {acc['name']}")
        return True
    else:
        print(f"Error: {result}")
        return False


def test_get_account_types():
    """Test GET /api/v1/accounts/types endpoint."""
    print("\n" + "=" * 60)
    print("TEST: Get all account types")
    print("=" * 60)

    result = call_api("/api/v1/accounts/types")

    if "result" in result:
        data = result["result"]
        print(f"Status: {data.get('status')}")
        print(f"Account types ({data.get('metadata', {}).get('count')}):")
        for acc_type in data.get("data", []):
            print(f"  - {acc_type}")
        return True
    else:
        print(f"Error: {result}")
        return False


def test_get_stats():
    """Test GET /api/v1/accounts/stats endpoint."""
    print("\n" + "=" * 60)
    print("TEST: Get account statistics")
    print("=" * 60)

    result = call_api("/api/v1/accounts/stats")

    if "result" in result:
        data = result["result"]
        if data.get("status") == "success":
            stats = data["data"]
            print(f"Total accounts: {stats['total_accounts']}")
            print(f"Reconcilable: {stats['reconcilable_count']}")
            print(f"Deprecated: {stats['deprecated_count']}")
            print("\nBy type:")
            for acc_type, count in sorted(stats["by_type"].items()):
                print(f"  {acc_type}: {count}")
            print("\nBy internal group:")
            for group, count in sorted(stats["by_internal_group"].items()):
                print(f"  {group}: {count}")
            return True
        print(f"Status: {data.get('status')}")
        print(f"Error: {data.get('error')}")
        return False
    else:
        print(f"Error: {result}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Accounting Accounts API Test Suite")
    print("=" * 60)

    if not login():
        print("Failed to login. Exiting.")
        return

    tests = [
        ("Get Accounts", test_get_accounts),
        ("Get Account by ID", test_get_account_by_id),
        ("Search Accounts", test_search_accounts),
        ("Get Account Types", test_get_account_types),
        ("Get Statistics", test_get_stats),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} - {test_name}")

    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")


if __name__ == "__main__":
    main()
