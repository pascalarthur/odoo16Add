# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class account_payment(models.TransientModel):
    _inherit = 'account.payment.register'

    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')
    manual_currency_rate = fields.Float('Rate', digits=(12, 6))

    @api.model
    def default_get(self, default_fields):
        rec = super(account_payment, self).default_get(default_fields)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec

        invoices = self.env['account.move'].browse(active_ids).filtered(
            lambda move: move.is_invoice(include_receipts=True))

        if (len(invoices) == 1):
            rec.update({
                'manual_currency_rate_active': invoices.manual_currency_rate_active,
                'manual_currency_rate': invoices.manual_currency_rate
            })
        return rec

    @api.model
    def _create_payment_vals_from_batch(self, batch_result):
        rec = super(account_payment, self)._create_payment_vals_from_batch(batch_result)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec

        account_move = self.env['account.move'].search([('name', '=', rec.get('ref'))]).ids
        for active_id in active_ids:
            if active_id in account_move:
                invoices = self.env['account.move'].browse(active_id).filtered(
                    lambda move: move.is_invoice(include_receipts=True))

                for invoice in invoices:
                    rec.update({
                        'manual_currency_rate_active': invoice.manual_currency_rate_active,
                        'manual_currency_rate': invoice.manual_currency_rate
                    })

                return rec
        return rec

    @api.depends('source_amount', 'source_amount_currency', 'source_currency_id', 'company_id', 'currency_id',
                 'payment_date', 'manual_currency_rate')
    def _compute_amount(self):

        for wizard in self:
            if wizard.source_currency_id == wizard.currency_id:
                # Same currency.
                wizard.amount = wizard.source_amount_currency
            else:
                # Foreign currency on payment different than the one set on the journal entries.
                amount_payment_currency = wizard.company_id.currency_id._convert(wizard.source_amount,
                                                                                 wizard.currency_id, wizard.company_id,
                                                                                 wizard.payment_date)
                wizard.amount = amount_payment_currency
        rec = super(account_payment, self)._compute_amount()

    @api.depends('amount')
    def _compute_payment_difference(self):

        for wizard in self:
            if wizard.source_currency_id == wizard.currency_id:
                # Same currency.
                wizard.payment_difference = wizard.source_amount_currency - wizard.amount
            else:
                # Foreign currency on payment different than the one set on the journal entries.
                amount_payment_currency = wizard.company_id.currency_id._convert(wizard.source_amount,
                                                                                 wizard.currency_id, wizard.company_id,
                                                                                 wizard.payment_date)
                wizard.payment_difference = amount_payment_currency - wizard.amount
        rec = super(account_payment, self)._compute_payment_difference()

    def _create_payment_vals_from_wizard(self, batch_result):
        res = super(account_payment, self)._create_payment_vals_from_wizard(batch_result)
        if self.manual_currency_rate_active:
            res.update({
                'manual_currency_rate_active': self.manual_currency_rate_active,
                'manual_currency_rate': self.manual_currency_rate
            })
        else:
            res.update({'manual_currency_rate_active': False, 'manual_currency_rate': 0.0})
        return res
