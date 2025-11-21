# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Tesote Binder.
Maps Tesote IDs to Odoo IDs following SOLID principles.
"""

# Handle both package and direct imports for testing
try:
    from ..utils.colored_logger import get_logger
except ImportError:
    from utils.colored_logger import get_logger

_logger = get_logger(__name__, category="sync")


class TesoteBinder:
    """
    Binder to map Tesote IDs ↔ Odoo IDs.
    Maintains mapping between external and internal identifiers.
    """

    def __init__(self, env, model_name: str, backend_id: int):
        """
        Initialize binder for a specific model.

        Args:
            env: Odoo environment
            model_name: Name of the Odoo model (e.g., 'tesote.account')
            backend_id: ID of the backend record
        """
        self.env = env
        self.model = env[model_name]
        self.model_name = model_name
        self.backend_id = backend_id

    def bind(self, external_id: str, odoo_id: int) -> None:
        """
        Create binding between Tesote ID and Odoo ID.

        Args:
            external_id: Tesote ID
            odoo_id: Odoo record ID
        """
        record = self.model.browse(odoo_id)
        if record.exists():
            record.write(
                {
                    "tesote_id": external_id,
                    "backend_id": self.backend_id,
                }
            )
            _logger.debug(f"Bound {self.model_name} Tesote ID {external_id} to Odoo ID {odoo_id}")

    def unbind(self, external_id: str) -> None:
        """
        Remove binding for Tesote ID.

        Args:
            external_id: Tesote ID to unbind
        """
        record = self.model.search(
            [
                ("tesote_id", "=", external_id),
                ("backend_id", "=", self.backend_id),
            ]
        )
        if record:
            record.write({"tesote_id": False})
            _logger.debug(f"Unbound {self.model_name} Tesote ID {external_id}")

    def to_internal(self, external_id: str, unwrap: bool = False):
        """
        Get Odoo ID from Tesote ID.

        Args:
            external_id: Tesote ID
            unwrap: If True, return browse record instead of ID

        Returns:
            Odoo record ID, browse record, or None if not found
        """
        binding = self.model.search(
            [
                ("tesote_id", "=", external_id),
                ("backend_id", "=", self.backend_id),
            ],
            limit=1,
        )

        if not binding:
            return None

        return binding if unwrap else binding.id

    def to_external(self, binding) -> str | None:
        """
        Get Tesote ID from Odoo binding.

        Args:
            binding: Odoo binding record or ID

        Returns:
            Tesote ID or None if not found
        """
        if isinstance(binding, int):
            binding = self.model.browse(binding)

        return binding.tesote_id if binding and binding.exists() else None

    def get_or_create(self, external_id: str, values: dict) -> tuple[int, bool]:
        """
        Get existing record or create new one with binding.

        Args:
            external_id: Tesote ID
            values: Values for creating new record

        Returns:
            Tuple of (Odoo ID, created) where created is True if new record
        """
        # Check if already exists
        odoo_id = self.to_internal(external_id)
        if odoo_id:
            return odoo_id, False

        # Create new record with binding
        values["tesote_id"] = external_id
        values["backend_id"] = self.backend_id
        record = self.model.create(values)
        _logger.info(f"Created new {self.model_name} ID {record.id} for Tesote ID {external_id}")
        return record.id, True
