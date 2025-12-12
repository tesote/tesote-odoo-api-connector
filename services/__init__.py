"""
Services package for ERP-agnostic business logic.

This package provides service layer implementations that are independent
of specific ERP systems (Odoo, SAP, etc.).
"""

from .authentication_service import AuthenticationService
from .base_accounting_service import BaseAccountingService


def get_accounting_service(erp_type="odoo", env=None) -> BaseAccountingService:
    """
    Factory to create accounting service for specific ERP.

    This factory pattern allows swapping ERP implementations without
    changing controller code (Dependency Inversion Principle).

    Args:
        erp_type: ERP system type ('odoo', 'sap', etc.)
        env: ERP-specific environment (Odoo env, SAP connection, etc.)

    Returns:
        BaseAccountingService implementation

    Raises:
        ValueError: If ERP type not supported or env not provided

    Example:
        >>> from services import get_accounting_service
        >>> service = get_accounting_service(erp_type='odoo', env=request.env)
        >>> accounts, cursor, has_more = service.get_accounts(limit=100)
    """
    if erp_type == "odoo":
        from .odoo_accounting_service import OdooAccountingService

        if not env:
            raise ValueError("Odoo service requires env parameter")

        return OdooAccountingService(env)

    elif erp_type == "sap":
        # Future: SAP implementation
        # from .sap_accounting_service import SapAccountingService
        # return SapAccountingService(env)
        raise ValueError("SAP service not yet implemented")

    else:
        raise ValueError(f"Unsupported ERP type: {erp_type}")


__all__ = [
    "AuthenticationService",
    "BaseAccountingService",
    "get_accounting_service",
]
