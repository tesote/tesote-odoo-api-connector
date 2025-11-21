# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

# ruff: noqa: I001
# Import order is critical for Odoo model inheritance
# tesote_binding MUST be imported before models that inherit from it
from . import tesote_account  # noqa: F401 - Inherits from tesote_binding
from . import tesote_backend  # noqa: F401
from . import tesote_binding  # noqa: F401 - Base model MUST be imported FIRST
from . import tesote_sync_log  # noqa: F401
from . import tesote_transaction  # noqa: F401 - Inherits from tesote_binding
from . import tesote_webhook_config  # noqa: F401
from . import tesote_webhook_event  # noqa: F401
from . import tesote_webhook_event_type  # noqa: F401
from . import tesote_webhook_monitor  # noqa: F401
from . import tesote_webhook_secret_wizard  # noqa: F401
