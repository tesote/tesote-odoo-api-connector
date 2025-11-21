# Copyright 2024 tesote.com
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Extension of res.currency for Tesote integration.

Adds computed fields to track which currencies are used by Tesote accounts
and provides methods to activate currencies for invoicing.
"""

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    """Extend res.currency with Tesote integration features."""

    _inherit = "res.currency"

    tesote_account_ids = fields.One2many(
        "tesote.account",
        "currency_id",
        string="Tesote Accounts",
        help="Tesote accounts using this currency",
    )

    tesote_account_count = fields.Integer(
        string="Tesote Account Count",
        compute="_compute_tesote_account_count",
        store=False,
        help="Number of Tesote accounts using this currency",
    )

    is_used_by_tesote = fields.Boolean(
        string="Used by Tesote",
        compute="_compute_tesote_account_count",
        store=False,
        help="Whether this currency is used by any Tesote account",
    )

    @api.depends("tesote_account_ids")
    def _compute_tesote_account_count(self):
        """Compute Tesote account count and usage flag."""
        for currency in self:
            count = len(currency.tesote_account_ids)
            currency.tesote_account_count = count
            currency.is_used_by_tesote = count > 0

    def action_activate_for_invoicing(self):
        """
        Activate this currency so it can be used in invoicing.

        This sets active=True on the currency record.
        """
        self.write({"active": True})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Currency Activated"),
                "message": _("Currency %s has been activated for invoicing.")
                % ", ".join(self.mapped("name")),
                "type": "success",
                "sticky": False,
            },
        }

    def action_deactivate(self):
        """
        Deactivate this currency.

        Note: The company's main currency cannot be deactivated.
        """
        company_currencies = self.env.companies.mapped("currency_id")
        to_deactivate = self - company_currencies

        if company_currencies & self:
            skipped = (company_currencies & self).mapped("name")
            _logger.warning(f"Cannot deactivate company currencies: {skipped}")

        if to_deactivate:
            to_deactivate.write({"active": False})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Currency Deactivated"),
                "message": _("Currency %s has been deactivated.")
                % ", ".join(to_deactivate.mapped("name")),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def activate_tesote_currencies(self):
        """
        Activate all currencies used by Tesote accounts.

        This is useful after importing accounts to ensure all their
        currencies are available for invoicing.

        Returns:
            dict: Action notification with result
        """
        # Find all currencies used by Tesote accounts
        tesote_currencies = self.env["tesote.account"].search([]).mapped("currency_id")

        if not tesote_currencies:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No Currencies"),
                    "message": _("No currencies found in Tesote accounts."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        # Find inactive currencies that need activation
        # Use with_context to include inactive records in search
        all_tesote_currency_names = tesote_currencies.mapped("name")
        inactive_currencies = self.with_context(active_test=False).search(
            [
                ("name", "in", all_tesote_currency_names),
                ("active", "=", False),
            ]
        )

        if inactive_currencies:
            inactive_currencies.write({"active": True})
            activated_names = inactive_currencies.mapped("name")
            _logger.info(f"Activated currencies for Tesote: {activated_names}")

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Currencies Activated"),
                    "message": _("Activated %d currencies: %s")
                    % (
                        len(inactive_currencies),
                        ", ".join(activated_names),
                    ),
                    "type": "success",
                    "sticky": False,
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Already Active"),
                    "message": _("All Tesote account currencies are already active."),
                    "type": "info",
                    "sticky": False,
                },
            }

    @api.model
    def get_tesote_currency_summary(self):
        """
        Get a summary of currencies used by Tesote accounts.

        Returns:
            dict: Summary with active/inactive currency counts and details
        """
        tesote_accounts = self.env["tesote.account"].search([])
        currency_ids = tesote_accounts.mapped("currency_id").ids

        if not currency_ids:
            return {
                "total": 0,
                "active": 0,
                "inactive": 0,
                "currencies": [],
            }

        # Get all currencies (including inactive) that match
        all_currencies = self.with_context(active_test=False).search(
            [
                ("id", "in", currency_ids),
            ]
        )

        active_currencies = all_currencies.filtered(lambda c: c.active)
        inactive_currencies = all_currencies.filtered(lambda c: not c.active)

        return {
            "total": len(all_currencies),
            "active": len(active_currencies),
            "inactive": len(inactive_currencies),
            "currencies": [
                {
                    "id": c.id,
                    "name": c.name,
                    "full_name": c.currency_unit_label or c.name,
                    "active": c.active,
                    "account_count": len(tesote_accounts.filtered(lambda a: a.currency_id == c)),
                }
                for c in all_currencies
            ],
        }
