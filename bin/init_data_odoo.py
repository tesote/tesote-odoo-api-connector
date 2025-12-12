"""
Initialize test data for accounting accounts in Odoo.
Run this script inside Odoo shell: docker compose exec odoo odoo shell -d tesote_dev < bin/init_data_odoo.py

NOTE: This script must be run inside Odoo shell where 'self' is available.
The 'self' variable is provided by Odoo shell context.
"""

# ruff: noqa: F821
# Get environment (self is provided by Odoo shell context)
env = self.env  # noqa: F821

print("=" * 60)
print("Initializing test data for Odoo accounting")
print("=" * 60)

# Get main company
company = env["res.company"].search([], limit=1)
print(f"\n Using company: {company.name} (ID: {company.id})")

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
    {
        "name": "Tech Solutions Inc",
        "email": "sales@techsolutions.com",
        "phone": "+1-555-0105",
        "is_company": True,
    },
]

created_partners = []
for partner_data in partners_data:
    # Check if partner already exists
    existing = env["res.partner"].search([("email", "=", partner_data["email"])], limit=1)
    if existing:
        print(f"  Partner {partner_data['name']} already exists")
        created_partners.append(existing)
    else:
        partner = env["res.partner"].create(partner_data)
        created_partners.append(partner)
        print(f"  Created partner: {partner_data['name']}")

print(f"\nCreated/found {len(created_partners)} partners")

# Check for accounts
accounts = env["account.account"].search([])
print(f"\nFound {len(accounts)} accounting accounts")

if len(accounts) > 0:
    print("\nSample accounts:")
    for acc in accounts[:10]:  # Show first 10
        print(f"  [{acc.code}] {acc.name} - Type: {acc.account_type}")

# Check for journals
journals = env["account.journal"].search([])
print(f"\nFound {len(journals)} journals")

if len(journals) > 0:
    print("\nJournals:")
    for journal in journals:
        print(f"  [{journal.code}] {journal.name} - Type: {journal.type}")

# Commit changes
env.cr.commit()

print("\n" + "=" * 60)
print("Test data initialization complete!")
print("=" * 60)
print("\nAccess Odoo at: http://localhost:8069")
print("Username: admin")
print("Password: admin")
print("Database: tesote_dev")
