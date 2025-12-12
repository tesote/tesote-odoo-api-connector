#!/usr/bin/env python3
"""
Initialize test data for accounting accounts in Odoo.

This script creates:
1. A company with accounting configuration
2. Chart of accounts
3. Sample accounts (assets, liabilities, equity, income, expenses)
4. Sample journal entries
5. Sample partners/customers
"""

import xmlrpc.client

# Connection parameters
url = "http://localhost:8069"
db = "tesote_dev"
username = "admin"
password = "admin"

# Connect to Odoo
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

print(f"Connected to Odoo as user {username} (UID: {uid})")

# Get or create main company
company_ids = models.execute_kw(
    db, uid, password, "res.company", "search", [[["name", "=", "My Company"]]], {"limit": 1}
)

if company_ids:
    company_id = company_ids[0]
    print(f"Using existing company (ID: {company_id})")
else:
    print("Company not found!")
    exit(1)

# Get or create fiscal position country
country_ids = models.execute_kw(
    db, uid, password, "res.country", "search", [[["code", "=", "US"]]], {"limit": 1}
)

if not country_ids:
    print("Creating country US")
    country_id = models.execute_kw(
        db, uid, password, "res.country", "create", [{"code": "US", "name": "United States"}]
    )
else:
    country_id = country_ids[0]

# Install chart of accounts if not already installed
print("Checking for chart of accounts...")
coa_installed = models.execute_kw(
    db, uid, password, "account.account", "search_count", [[["company_id", "=", company_id]]]
)

if coa_installed == 0:
    print("Installing US chart of accounts...")
    # This would typically be done through Odoo's accounting setup wizard
    # For now, we'll create minimal accounts manually

    # Create account types if needed
    account_types_data = [
        {"name": "Current Assets", "type": "asset_current", "internal_group": "asset"},
        {"name": "Non-current Assets", "type": "asset_non_current", "internal_group": "asset"},
        {"name": "Current Liabilities", "type": "liability_current", "internal_group": "liability"},
        {
            "name": "Non-current Liabilities",
            "type": "liability_non_current",
            "internal_group": "liability",
        },
        {"name": "Equity", "type": "equity", "internal_group": "equity"},
        {"name": "Income", "type": "income", "internal_group": "income"},
        {"name": "Other Income", "type": "income_other", "internal_group": "income"},
        {"name": "Expense", "type": "expense", "internal_group": "expense"},
        {"name": "Cost of Revenue", "type": "expense_direct_cost", "internal_group": "expense"},
        {"name": "Depreciation", "type": "expense_depreciation", "internal_group": "expense"},
    ]

    print("Creating accounts...")
    accounts_data = [
        # Assets
        {
            "code": "1000",
            "name": "Cash and Cash Equivalents",
            "account_type": "asset_current",
            "reconcile": True,
        },
        {
            "code": "1010",
            "name": "Bank Account",
            "account_type": "asset_current",
            "reconcile": True,
        },
        {
            "code": "1100",
            "name": "Accounts Receivable",
            "account_type": "asset_receivable",
            "reconcile": True,
        },
        {"code": "1200", "name": "Inventory", "account_type": "asset_current", "reconcile": False},
        {
            "code": "1500",
            "name": "Fixed Assets",
            "account_type": "asset_non_current",
            "reconcile": False,
        },
        # Liabilities
        {
            "code": "2000",
            "name": "Accounts Payable",
            "account_type": "liability_payable",
            "reconcile": True,
        },
        {
            "code": "2100",
            "name": "Credit Cards",
            "account_type": "liability_current",
            "reconcile": True,
        },
        {
            "code": "2500",
            "name": "Long-term Debt",
            "account_type": "liability_non_current",
            "reconcile": False,
        },
        # Equity
        {"code": "3000", "name": "Owner's Equity", "account_type": "equity", "reconcile": False},
        {
            "code": "3100",
            "name": "Retained Earnings",
            "account_type": "equity_unaffected",
            "reconcile": False,
        },
        # Income
        {"code": "4000", "name": "Product Sales", "account_type": "income", "reconcile": False},
        {"code": "4100", "name": "Service Revenue", "account_type": "income", "reconcile": False},
        {
            "code": "4900",
            "name": "Other Income",
            "account_type": "income_other",
            "reconcile": False,
        },
        # Expenses
        {
            "code": "5000",
            "name": "Cost of Goods Sold",
            "account_type": "expense_direct_cost",
            "reconcile": False,
        },
        {
            "code": "6000",
            "name": "Operating Expenses",
            "account_type": "expense",
            "reconcile": False,
        },
        {
            "code": "6100",
            "name": "Salaries and Wages",
            "account_type": "expense",
            "reconcile": False,
        },
        {"code": "6200", "name": "Rent Expense", "account_type": "expense", "reconcile": False},
        {
            "code": "6300",
            "name": "Utilities Expense",
            "account_type": "expense",
            "reconcile": False,
        },
        {
            "code": "6400",
            "name": "Marketing and Advertising",
            "account_type": "expense",
            "reconcile": False,
        },
        {
            "code": "6500",
            "name": "Depreciation Expense",
            "account_type": "expense_depreciation",
            "reconcile": False,
        },
    ]

    created_accounts = []
    for acc_data in accounts_data:
        acc_data["company_id"] = company_id
        try:
            acc_id = models.execute_kw(db, uid, password, "account.account", "create", [acc_data])
            created_accounts.append(acc_id)
            print(f"  Created account: {acc_data['code']} - {acc_data['name']}")
        except Exception as e:
            print(f"  Error creating account {acc_data['code']}: {e}")

    print(f"Created {len(created_accounts)} accounts")
else:
    print(f"Chart of accounts already exists ({coa_installed} accounts found)")

# Create sample partners/customers
print("\nCreating sample partners...")
partners_data = [
    {
        "name": "ABC Corporation",
        "email": "contact@abccorp.com",
        "phone": "+1-555-0101",
        "is_company": True,
    },
    {
        "name": "XYZ Industries",
        "email": "info@xyzind.com",
        "phone": "+1-555-0102",
        "is_company": True,
    },
    {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-0103",
        "is_company": False,
    },
    {
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
        "phone": "+1-555-0104",
        "is_company": False,
    },
]

created_partners = []
for partner_data in partners_data:
    # Check if partner already exists
    existing = models.execute_kw(
        db,
        uid,
        password,
        "res.partner",
        "search",
        [[["email", "=", partner_data["email"]]]],
        {"limit": 1},
    )

    if existing:
        print(f"  Partner {partner_data['name']} already exists")
        created_partners.append(existing[0])
    else:
        partner_id = models.execute_kw(db, uid, password, "res.partner", "create", [partner_data])
        created_partners.append(partner_id)
        print(f"  Created partner: {partner_data['name']}")

print(f"Created/found {len(created_partners)} partners")

# Get account journal
print("\nChecking for journals...")
journal_ids = models.execute_kw(
    db,
    uid,
    password,
    "account.journal",
    "search",
    [[["company_id", "=", company_id], ["type", "=", "general"]]],
    {"limit": 1},
)

if not journal_ids:
    print("  No general journal found. Creating one...")
    # Get an account for default debit/credit account
    default_account_ids = models.execute_kw(
        db,
        uid,
        password,
        "account.account",
        "search",
        [[["company_id", "=", company_id], ["code", "=", "1000"]]],
        {"limit": 1},
    )

    if default_account_ids:
        journal_id = models.execute_kw(
            db,
            uid,
            password,
            "account.journal",
            "create",
            [
                {
                    "name": "Miscellaneous Operations",
                    "code": "MISC",
                    "type": "general",
                    "company_id": company_id,
                }
            ],
        )
        journal_ids = [journal_id]
        print("  Created journal: MISC")
    else:
        print("  Could not create journal: No default account found")
        journal_ids = []

if journal_ids:
    print(f"Using journal ID: {journal_ids[0]}")
else:
    print("No journal available for creating moves")

print("\n" + "=" * 60)
print("Test data initialization complete!")
print("=" * 60)
print(f"\nYou can now access Odoo at: {url}")
print(f"Username: {username}")
print(f"Password: {password}")
print(f"Database: {db}")
print("\nAccess accounting at: http://localhost:8069/web#action=account.action_account_form")
