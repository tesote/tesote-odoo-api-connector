# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Pytest configuration and fixtures for testing without Odoo.
This file must be imported/executed before any Odoo imports.
"""

import sys
from unittest.mock import MagicMock

# Mock Odoo modules BEFORE any imports - this is critical!
# These mocks must be set up before any module tries to import from odoo
sys.modules["odoo"] = MagicMock()
sys.modules["odoo.exceptions"] = MagicMock()
sys.modules["odoo.models"] = MagicMock()
sys.modules["odoo.fields"] = MagicMock()
sys.modules["odoo.api"] = MagicMock()
sys.modules["odoo.tools"] = MagicMock()
sys.modules["odoo.http"] = MagicMock()


# Create mock classes
class MockModel:
    """Mock Odoo Model class."""

    pass


class MockFields:
    """Mock Odoo Fields."""

    Char = MagicMock()
    Text = MagicMock()
    Integer = MagicMock()
    Float = MagicMock()
    Boolean = MagicMock()
    Date = MagicMock()
    Datetime = MagicMock()
    Selection = MagicMock()
    Many2one = MagicMock()
    One2many = MagicMock()
    Many2many = MagicMock()
    Html = MagicMock()
    Monetary = MagicMock()


class MockApi:
    """Mock Odoo API decorators."""

    @staticmethod
    def model(func):
        return func

    @staticmethod
    def model_create_multi(func):
        return func

    @staticmethod
    def depends(*args):
        def decorator(func):
            return func

        return decorator

    @staticmethod
    def constrains(*args):
        def decorator(func):
            return func

        return decorator


class MockUserError(Exception):
    """Mock UserError exception."""

    pass


class MockHttp:
    """Mock Odoo HTTP module."""

    Controller = object

    @staticmethod
    def route(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


# Set up the mocks
sys.modules["odoo"].models.Model = MockModel
sys.modules["odoo"].fields = MockFields()
sys.modules["odoo"].api = MockApi()
sys.modules["odoo.exceptions"].UserError = MockUserError
sys.modules["odoo"].http = MockHttp()


# Mock the translation function
def mock_translate(text, **kwargs):
    """Mock translation function with keyword argument support."""
    if kwargs:
        return text % kwargs
    return text


sys.modules["odoo"]._ = mock_translate
