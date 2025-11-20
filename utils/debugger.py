# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Debugger Utilities for Development.
Provides debugpy integration for remote debugging with VSCode/PyCharm.
"""

import logging
import os

_logger = logging.getLogger(__name__)


def init_debugger(wait_for_attach: bool = False, port: int = 5678):
    """
    Initialize debugpy for remote debugging.

    This should be called at module initialization in development mode.

    Args:
        wait_for_attach: If True, will pause execution until debugger attaches
        port: Port for debugger to listen on (default: 5678)

    Usage:
        Add to your module's __init__.py in development:

        ```python
        from .utils.debugger import init_debugger
        init_debugger()
        ```

        Then in VSCode, use the "Python: Attach to Odoo" configuration.
    """
    # Only enable in development mode
    is_dev = os.environ.get("ODOO_ENV", "production").lower() in ["development", "dev"]
    debug_enabled = os.environ.get("ENABLE_DEBUGPY", "false").lower() == "true"

    if not (is_dev and debug_enabled):
        return

    try:
        import debugpy

        # Check if already listening
        if debugpy.is_client_connected():
            _logger.info("Debugger already connected")
            return

        # Start debugpy listener
        try:
            debugpy.listen(("0.0.0.0", port))
            _logger.info(f"🐛 Debugger listening on port {port}")
            _logger.info("💡 Attach your debugger now!")

            if wait_for_attach:
                _logger.info("⏸️  Waiting for debugger to attach...")
                debugpy.wait_for_client()
                _logger.info("✓ Debugger attached!")

        except Exception as e:
            # Port might already be in use
            _logger.warning(f"Debugger already running or port in use: {e}")

    except ImportError:
        _logger.warning(
            "debugpy not installed. Install with: pip install debugpy\n"
            "Or add to pyproject.toml dev dependencies"
        )


def breakpoint_here():
    """
    Set a breakpoint at this location.

    More explicit than Python's built-in breakpoint() for team clarity.

    Usage:
        ```python
        from ..utils.debugger import breakpoint_here

        def my_function():
            # ... code ...
            breakpoint_here()  # Execution will pause here when debugger attached
            # ... more code ...
        ```
    """
    try:
        import debugpy

        if debugpy.is_client_connected():
            debugpy.breakpoint()
        else:
            # Fallback to standard breakpoint
            breakpoint()
    except ImportError:
        # Use standard Python breakpoint
        breakpoint()


def log_debug_info(obj, name: str = "Object"):
    """
    Log detailed debug information about an object.

    Args:
        obj: Object to inspect
        name: Name for the object in logs
    """
    _logger.debug(f"=== DEBUG INFO: {name} ===")
    _logger.debug(f"Type: {type(obj)}")
    _logger.debug(f"Value: {obj}")

    if hasattr(obj, "__dict__"):
        _logger.debug(f"Attributes: {obj.__dict__}")

    if isinstance(obj, (list, tuple)) and len(obj) > 0:
        _logger.debug(f"Length: {len(obj)}")
        _logger.debug(f"First item: {obj[0]}")

    if isinstance(obj, dict) and len(obj) > 0:
        _logger.debug(f"Keys: {list(obj.keys())}")

    _logger.debug("=" * (14 + len(name)))
