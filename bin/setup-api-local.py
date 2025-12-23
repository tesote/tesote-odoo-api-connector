#!/usr/bin/env python3
"""
Setup script for local API testing.
Creates backend and webhook config, outputs secret key for Postman.
"""

import secrets
import xmlrpc.client

# Configuration - adjust if needed
ODOO_URL = "http://localhost:8069"
DB_NAME = "tesote_dev"
USERNAME = "admin"
PASSWORD = "admin"


def main():
    print("=" * 50)
    print("Tesote Accounting API - Local Setup")
    print("=" * 50)
    print()

    # Connect to Odoo
    print(f"Connecting to {ODOO_URL}...")
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")

    try:
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        if not uid:
            print("❌ Authentication failed. Check credentials.")
            print(f"   DB: {DB_NAME}, User: {USERNAME}")
            return
        print(f"✅ Connected as user ID: {uid}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"   Make sure Odoo is running at {ODOO_URL}")
        return

    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

    # Check for existing backend
    print()
    print("Checking for existing backend...")
    existing_backends = models.execute_kw(
        DB_NAME, uid, PASSWORD,
        'tesote.backend', 'search_read',
        [[]],
        {'fields': ['id', 'name']}
    )

    if existing_backends:
        backend_id = existing_backends[0]['id']
        print(f"✅ Found existing backend: {existing_backends[0]['name']} (ID: {backend_id})")
    else:
        print("Creating new backend...")
        backend_id = models.execute_kw(
            DB_NAME, uid, PASSWORD,
            'tesote.backend', 'create',
            [{
                'name': 'Local API Backend',
                'api_url': 'https://api.tesote.com',
                'api_token': 'local-dev-token',
                'api_version': 'v2'
            }]
        )
        print(f"✅ Created backend ID: {backend_id}")

    # Check for existing webhook config
    print()
    print("Checking for existing webhook config...")
    existing_webhooks = models.execute_kw(
        DB_NAME, uid, PASSWORD,
        'tesote.webhook.config', 'search_read',
        [[('backend_id', '=', backend_id)]],
        {'fields': ['id', 'secret_key', 'enabled']}
    )

    if existing_webhooks:
        webhook = existing_webhooks[0]
        secret_key = webhook['secret_key']
        print(f"✅ Found existing webhook config (ID: {webhook['id']})")
        if not webhook['enabled']:
            print("   ⚠️  Webhook is disabled, enabling...")
            models.execute_kw(
                DB_NAME, uid, PASSWORD,
                'tesote.webhook.config', 'write',
                [[webhook['id']], {'enabled': True}]
            )
    else:
        print("Creating new webhook config...")
        secret_key = secrets.token_urlsafe(32)
        webhook_id = models.execute_kw(
            DB_NAME, uid, PASSWORD,
            'tesote.webhook.config', 'create',
            [{
                'backend_id': backend_id,
                'enabled': True,
                'secret_key': secret_key
            }]
        )
        print(f"✅ Created webhook config ID: {webhook_id}")

    # Output results
    print()
    print("=" * 50)
    print("🎉 SETUP COMPLETE!")
    print("=" * 50)
    print()
    print("Your secret key for Postman:")
    print()
    print(f"   {secret_key}")
    print()
    print("Next steps:")
    print("1. Import 'Tesote_Accounting_API.postman_collection.json' into Postman")
    print("2. Edit collection variables and replace 'YOUR_SECRET_KEY_HERE' with:")
    print(f"   {secret_key}")
    print("3. Send requests!")
    print()
    print("Test endpoints:")
    print(f"   GET  {ODOO_URL}/tesote/api/v1/accounting/accounts")
    print(f"   GET  {ODOO_URL}/tesote/api/v1/accounting/accounts/types")
    print(f"   GET  {ODOO_URL}/tesote/api/v1/accounting/accounts/stats")
    print()


if __name__ == "__main__":
    main()
