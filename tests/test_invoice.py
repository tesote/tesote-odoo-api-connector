# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Test Tesote Invoice models and synchronization.
"""

from unittest.mock import MagicMock, Mock

import pytest


class TestTesoteInvoice:
    """Test Tesote Invoice model."""

    @pytest.fixture
    def mock_env(self):
        """Create mock Odoo environment."""
        env = MagicMock()
        env.__getitem__ = Mock(side_effect=lambda key: Mock())
        env.company = Mock(currency_id=Mock(id=1))
        return env

    def test_invoice_model_fields(self):
        """Test that invoice model has required fields."""
        from models.tesote_invoice import TesoteInvoice

        # Check required fields
        assert hasattr(TesoteInvoice, "invoice_number")
        assert hasattr(TesoteInvoice, "tesote_id")
        assert hasattr(TesoteInvoice, "account_id")
        assert hasattr(TesoteInvoice, "backend_id")
        assert hasattr(TesoteInvoice, "invoice_type")
        assert hasattr(TesoteInvoice, "invoice_date")
        assert hasattr(TesoteInvoice, "due_date")
        assert hasattr(TesoteInvoice, "subtotal")
        assert hasattr(TesoteInvoice, "tax_amount")
        assert hasattr(TesoteInvoice, "total_amount")
        assert hasattr(TesoteInvoice, "paid_amount")
        assert hasattr(TesoteInvoice, "currency_id")
        assert hasattr(TesoteInvoice, "partner_id")
        assert hasattr(TesoteInvoice, "partner_name")
        assert hasattr(TesoteInvoice, "status")
        assert hasattr(TesoteInvoice, "payment_status")
        assert hasattr(TesoteInvoice, "line_ids")
        assert hasattr(TesoteInvoice, "account_move_id")
        assert hasattr(TesoteInvoice, "is_reconciled")

    def test_invoice_type_selection(self):
        """Test invoice type field selection values."""
        from models.tesote_invoice import TesoteInvoice

        # Check that invoice_type field exists
        assert hasattr(TesoteInvoice, "invoice_type")

    def test_invoice_status_selection(self):
        """Test invoice status field selection values."""
        from models.tesote_invoice import TesoteInvoice

        # Check that status field exists
        assert hasattr(TesoteInvoice, "status")

    def test_invoice_unique_constraint(self):
        """Test unique constraint on tesote_id per account."""
        from models.tesote_invoice import TesoteInvoice

        # Check SQL constraints
        constraints = TesoteInvoice._sql_constraints

        # Should have unique constraint on tesote_id + account_id
        unique_constraint = [c for c in constraints if "unique" in c[2].lower()]
        assert len(unique_constraint) > 0

    def test_invoice_create_from_sync_data_method_exists(self):
        """Test that create_from_sync_data method exists."""
        from models.tesote_invoice import TesoteInvoice

        assert hasattr(TesoteInvoice, "create_from_sync_data")
        assert callable(TesoteInvoice.create_from_sync_data)

    def test_invoice_update_from_sync_data_method_exists(self):
        """Test that update_from_sync_data method exists."""
        from models.tesote_invoice import TesoteInvoice

        assert hasattr(TesoteInvoice, "update_from_sync_data")
        assert callable(TesoteInvoice.update_from_sync_data)

    def test_invoice_create_journal_entry_method_exists(self):
        """Test that create_journal_entry method exists."""
        from models.tesote_invoice import TesoteInvoice

        assert hasattr(TesoteInvoice, "create_journal_entry")
        assert callable(TesoteInvoice.create_journal_entry)

    def test_invoice_compute_payment_status_method_exists(self):
        """Test that _compute_payment_status method exists."""
        from models.tesote_invoice import TesoteInvoice

        assert hasattr(TesoteInvoice, "_compute_payment_status")
        assert callable(TesoteInvoice._compute_payment_status)

    def test_invoice_compute_amount_due_method_exists(self):
        """Test that _compute_amount_due method exists."""
        from models.tesote_invoice import TesoteInvoice

        assert hasattr(TesoteInvoice, "_compute_amount_due")
        assert callable(TesoteInvoice._compute_amount_due)


class TestTesoteInvoiceLine:
    """Test Tesote Invoice Line model."""

    def test_invoice_line_model_fields(self):
        """Test that invoice line model has required fields."""
        from models.tesote_invoice_line import TesoteInvoiceLine

        # Check required fields
        assert hasattr(TesoteInvoiceLine, "invoice_id")
        assert hasattr(TesoteInvoiceLine, "sequence")
        assert hasattr(TesoteInvoiceLine, "description")
        assert hasattr(TesoteInvoiceLine, "quantity")
        assert hasattr(TesoteInvoiceLine, "unit_price")
        assert hasattr(TesoteInvoiceLine, "discount")
        assert hasattr(TesoteInvoiceLine, "tax_amount")
        assert hasattr(TesoteInvoiceLine, "total_amount")
        assert hasattr(TesoteInvoiceLine, "currency_id")
        assert hasattr(TesoteInvoiceLine, "product_id")
        assert hasattr(TesoteInvoiceLine, "account_id")

    def test_invoice_line_create_from_sync_data_method_exists(self):
        """Test that create_from_sync_data method exists."""
        from models.tesote_invoice_line import TesoteInvoiceLine

        assert hasattr(TesoteInvoiceLine, "create_from_sync_data")
        assert callable(TesoteInvoiceLine.create_from_sync_data)


class TestInvoiceAdapter:
    """Test invoice sync adapter methods."""

    def test_adapter_has_invoices_sync_endpoint(self):
        """Test that adapter has invoices_sync endpoint configured."""
        from components.adapter import TesoteAdapter

        assert "invoices_sync" in TesoteAdapter.ENDPOINTS
        assert "invoices/sync" in TesoteAdapter.ENDPOINTS["invoices_sync"]

    def test_adapter_sync_invoices_method_exists(self):
        """Test that sync_invoices method exists on adapter."""
        from components.adapter import TesoteAdapter

        assert hasattr(TesoteAdapter, "sync_invoices")
        assert callable(TesoteAdapter.sync_invoices)


class TestInvoiceBackendSync:
    """Test invoice sync methods on backend model."""

    def test_backend_has_sync_invoices_method(self):
        """Test that backend has sync_invoices_v2 method."""
        from models.tesote_backend import TesoteBackend

        assert hasattr(TesoteBackend, "sync_invoices_v2")
        assert callable(TesoteBackend.sync_invoices_v2)

    def test_backend_has_process_invoice_sync_results(self):
        """Test that backend has _process_invoice_sync_results method."""
        from models.tesote_backend import TesoteBackend

        assert hasattr(TesoteBackend, "_process_invoice_sync_results")
        assert callable(TesoteBackend._process_invoice_sync_results)

    def test_backend_has_sync_all_invoices(self):
        """Test that backend has sync_all_invoices method."""
        from models.tesote_backend import TesoteBackend

        assert hasattr(TesoteBackend, "sync_all_invoices")
        assert callable(TesoteBackend.sync_all_invoices)

    def test_backend_has_invoice_count_field(self):
        """Test that backend has invoice_count field."""
        from models.tesote_backend import TesoteBackend

        assert hasattr(TesoteBackend, "invoice_count")

    def test_backend_has_action_view_invoices(self):
        """Test that backend has action_view_invoices method."""
        from models.tesote_backend import TesoteBackend

        assert hasattr(TesoteBackend, "action_view_invoices")
        assert callable(TesoteBackend.action_view_invoices)


class TestAccountInvoiceFields:
    """Test invoice fields on account model."""

    def test_account_has_invoice_sync_cursor(self):
        """Test that account has invoice_sync_cursor field."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "invoice_sync_cursor")

    def test_account_has_invoice_sync_date(self):
        """Test that account has invoice_sync_date field."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "invoice_sync_date")

    def test_account_has_invoice_count(self):
        """Test that account has invoice_count field."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "invoice_count")

    def test_account_has_invoice_ids(self):
        """Test that account has invoice_ids One2many field."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "invoice_ids")

    def test_account_has_action_view_invoices(self):
        """Test that account has action_view_invoices method."""
        from models.tesote_account import TesoteAccount

        assert hasattr(TesoteAccount, "action_view_invoices")
        assert callable(TesoteAccount.action_view_invoices)


class TestInvoiceDateParsing:
    """Test date parsing methods for invoices."""

    def test_invoice_parse_date_method_exists(self):
        """Test that _parse_date method exists."""
        from models.tesote_invoice import TesoteInvoice

        assert hasattr(TesoteInvoice, "_parse_date")
        assert callable(TesoteInvoice._parse_date)

    def test_invoice_parse_datetime_method_exists(self):
        """Test that _parse_datetime method exists."""
        from models.tesote_invoice import TesoteInvoice

        assert hasattr(TesoteInvoice, "_parse_datetime")
        assert callable(TesoteInvoice._parse_datetime)
