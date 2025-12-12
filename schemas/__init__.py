"""
Generic schemas for API responses.

These schemas are ERP-agnostic and can be used across Odoo, SAP, etc.
"""

from .account_schema import AccountSchema

__all__ = ["AccountSchema"]
