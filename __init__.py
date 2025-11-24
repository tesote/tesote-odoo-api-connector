# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

# Initialize debugger for development (must be before other imports)
try:
    from .utils.debugger import init_debugger

    # Initialize debugger - will only activate if ENABLE_DEBUGPY=true in env
    init_debugger(wait_for_attach=False, port=5678)
except ImportError:
    # debugpy not installed or running in test environment
    pass
except Exception:
    # Don't let debugger initialization block module loading
    pass

# Initialize Sentry error tracking early (before other imports)
try:
    from .utils import sentry_config

    sentry_config.init_sentry()
except ImportError:
    # Sentry not available or running in test environment
    pass
except Exception:
    # Don't let Sentry initialization block module loading
    pass

# Only import when running in Odoo context
# Tests will mock these modules
try:
    from . import components, controllers, models, utils
except ImportError:
    # Running in test environment
    pass


def post_init_hook(env):
    """
    Post-initialization hook to run database migrations.
    This runs after the module is installed/upgraded.

    Args:
        env: Odoo environment (Odoo 18.0+ signature)
    """
    # Handle both package and direct imports for testing
    try:
        from .utils.colored_logger import get_logger
    except ImportError:
        from utils.colored_logger import get_logger

    _logger = get_logger(__name__)

    _logger.info("Running tesote_connector post-initialization")

    try:
        # Import here to avoid circular imports
        from .migrations.migrate import migrate as run_migrations

        # Run database migrations
        cr = env.cr
        version = env.registry.version if hasattr(env, "registry") else "18.0.1.0.0"
        run_migrations(cr, version)
        _logger.info("Database migrations completed successfully")
    except Exception as e:
        _logger.error(f"Migration failed during post_init_hook: {e}")
        # Don't re-raise to avoid blocking module installation
        # Users can run migrations manually if needed


def pre_uninstall_hook(env):
    """
    Hook executed before module uninstallation.

    Logs comprehensive information about data that will be deleted.
    This provides visibility beyond Odoo's standard uninstall preview.

    Args:
        env: Odoo environment (Odoo 18.0+ signature)
    """
    # Handle both package and direct imports for testing
    try:
        from .utils.colored_logger import get_logger
    except ImportError:
        from utils.colored_logger import get_logger

    _logger = get_logger(__name__)

    cr = env.cr

    _logger.warning("=" * 80)
    _logger.warning("TESOTE CONNECTOR - PRE-UNINSTALL DATA SUMMARY")
    _logger.warning("=" * 80)
    _logger.warning("The following data will be PERMANENTLY DELETED:")
    _logger.warning("")

    # Query all tesote_connector tables and count records
    tables = [
        ("tesote_backend", "Backend Configurations"),
        ("tesote_account", "Synced Accounts"),
        ("tesote_transaction", "Synced Transactions"),
        ("tesote_sync_log", "Sync History Logs"),
        ("tesote_webhook_config", "Webhook Configurations"),
        ("tesote_webhook_event", "Webhook Event History"),
        ("tesote_webhook_event_type", "Webhook Event Types"),
        ("tesote_webhook_monitor", "Webhook Monitoring Data"),
        ("tesote_webhook_secret_wizard", "Wizard Records"),
    ]

    total_records = 0

    for table_name, description in tables:
        try:
            cr.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cr.fetchone()[0]
            total_records += count

            if count > 0:
                _logger.warning(f"  - {description:30} : {count:6} records")
            else:
                _logger.warning(f"  - {description:30} : {count:6} records (empty)")

        except Exception as e:
            # Table might not exist if module was never fully installed
            _logger.warning(f"  - {description:30} : (table not found)")

    _logger.warning("")
    _logger.warning(f"TOTAL RECORDS TO BE DELETED: {total_records}")
    _logger.warning("")
    _logger.warning("Additional items to be removed:")
    _logger.warning("  - All menu items and views")
    _logger.warning("  - All scheduled actions (cron jobs)")
    _logger.warning("  - All access rights and security rules")
    _logger.warning("  - All ir.model.access records")
    _logger.warning("")
    _logger.warning("⚠️  THIS OPERATION CANNOT BE UNDONE")
    _logger.warning("⚠️  Ensure you have a database backup before proceeding")
    _logger.warning("=" * 80)
