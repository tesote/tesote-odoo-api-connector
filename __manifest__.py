# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

{
    "name": "tesote.com Connector",
    "version": "18.0.1.0.0",
    "author": "tesote.com",
    "maintainer": "tesote.com",
    "website": "https://github.com/tesote/tesote-odoo-api-connector",
    "license": "LGPL-3",
    "category": "Accounting/Accounting",
    "summary": "Enterprise-grade financial data synchronization from tesote.com API v2 - Real-time accounts, transactions, and webhook integration",
    "description": """
tesote.com Connector for Odoo 18.0
===================================

Professional integration for synchronizing financial data from tesote.com with Odoo ERP.

Overview
--------
The tesote.com Connector provides seamless integration between tesote.com financial platform
and Odoo 18.0, enabling automated synchronization of accounts, transactions, and balance data.
Built for enterprise deployments with comprehensive error handling, multi-language support,
and real-time webhook capabilities.

Core Features
-------------
* Real-time synchronization of financial accounts and transaction data
* Cursor-based incremental updates for efficient data transfer
* Automatic transaction lifecycle management (pending to completed states)
* Secure webhook integration with HMAC-SHA256 signature verification
* Comprehensive sync logging and monitoring dashboard
* Multi-company support with singleton backend configuration
* Full internationalization (English and Spanish)

Financial Data Management
-------------------------
* Automatic account balance tracking with timestamp precision
* Transaction categorization and counterparty management
* Support for multiple currencies via Odoo currency master
* Transaction status tracking (pending/completed)
* Account reconciliation preparation

Technical Architecture
----------------------
* tesote.com API v2.0.0 compliance
* RESTful endpoint integration with cursor-based pagination
* Rate limiting support for Standard, Premium, and Enterprise tiers
* Scheduled synchronization via Odoo cron jobs
* Extensible mapper and adapter pattern for customization
* Database migration framework for seamless upgrades

Webhook Integration
-------------------
* Real-time event processing for sync triggers
* Idempotent webhook handling with duplicate detection
* Configurable event subscriptions (accounts, transactions, sync updates)
* Webhook monitoring dashboard with success rate tracking
* Automatic retry logic with exponential backoff
* Alert notifications for webhook failures

Security & Compliance
---------------------
* Bearer token authentication
* HMAC-SHA256 webhook signature verification
* Secure credential storage
* Audit trail for all synchronization operations
* Access control via Odoo security groups

Deployment Support
------------------
* Self-hosted Odoo installations
* Odoo.sh cloud platform
* Docker development environment included
* Comprehensive test suite (112 tests)
* Production-ready with comprehensive error handling

Use Cases
---------
* Automated financial data aggregation from tesote.com
* Real-time transaction monitoring and reconciliation
* Multi-account balance tracking
* Financial reporting and analytics integration
* Enterprise financial operations automation

Documentation & Support
-----------------------
* Complete API documentation included
* Migration guides for schema evolution
* Troubleshooting documentation
* GitHub issue tracker
* Professional support available

Requirements
------------
* Odoo 18.0
* Python requests library
* tesote.com API v2 account and credentials
* PostgreSQL database

For more information, visit: https://github.com/tesote/tesote-odoo-api-connector
API Documentation: https://equipo.tesote.com/api/docs?version=v2
    """,
    "depends": [
        "account",
        "base",
    ],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "data/webhook_monitoring_cron.xml",
        "views/tesote_backend_views.xml",
        "views/tesote_account_views.xml",
        "views/tesote_transaction_views.xml",
        "views/tesote_sync_log_views.xml",
        "views/tesote_webhook_config_views.xml",
        "views/tesote_webhook_event_views.xml",
        "views/tesote_webhook_secret_wizard_views.xml",
        "views/tesote_menu.xml",
    ],
    "post_init_hook": "post_init_hook",
    "pre_uninstall_hook": "pre_uninstall_hook",
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_1.png",
        "static/description/screenshot_2.png",
        "static/description/icon.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "development_status": "Production/Stable",
    "maintainers": ["tesote"],
    "price": 0.00,
    "currency": "EUR",
    "support": "support-odoo@tesote.com",
}
