from typing import List
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def compute_converted_prices(self):
        for order in self:
            for line in order.lines:
                line.converted_prices.unlink()
                for currency in order.config_id.selected_currencies:
                    converted_price = line.original_price * currency.rate
                    line.converted_prices.create({
                        'line_id': line.id,
                        'currency_id': currency.id,
                        'price': converted_price,
                    })

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        self.compute_converted_prices()
        print('action_pos_order_paid')
        return res


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.constrains('pricelist_id', 'use_pricelist', 'available_pricelist_ids', 'journal_id', 'invoice_journal_id', 'payment_method_ids')
    def _check_currencies(self):
        for config in self:
            if config.use_pricelist and config.pricelist_id and config.pricelist_id not in config.available_pricelist_ids:
                raise ValidationError(_("The default pricelist must be included in the available pricelists."))

            # # Check if the config's payment methods are compatible with its currency
            # for pm in config.payment_method_ids:
            #     if pm.journal_id and pm.journal_id.currency_id and pm.journal_id.currency_id != config.currency_id:
            #         raise ValidationError(_("All payment methods must be in the same currency as the Sales Journal or the company currency if that is not set."))

        if any(self.available_pricelist_ids.mapped(lambda pricelist: pricelist.currency_id != self.currency_id)):
            raise ValidationError(_("All available pricelists must be in the same currency as the company or"
                                    " as the Sales Journal set on this point of sale if you use"
                                    " the Accounting application."))
        if self.invoice_journal_id.currency_id and self.invoice_journal_id.currency_id != self.currency_id:
            raise ValidationError(_("The invoice journal must be in the same currency as the Sales Journal or the company currency if that is not set."))


class PosSession(models.Model):
    _inherit = 'pos.session'

    alternative_cash_journal_ids = fields.Many2many('account.journal', compute='_compute_alternative_cash_journal_ids', store=True)

    @api.depends('cash_journal_id')
    def _compute_alternative_cash_journal_ids(self):
        # Only one cash register is supported by point_of_sale.
        for session in self:
            alternative_cash_journal_ids = session.payment_method_ids.filtered('is_cash_count')[1:].mapped('journal_id')
            session.alternative_cash_journal_ids = alternative_cash_journal_ids

    def set_cashbox_pos_multi_currency(self, cashbox_values: List[dict]):
        for cashbox in cashbox_values:
            print(cashbox)
            openingCash = float(cashbox['openingCash'])
            self.sudo()._post_statement_difference_multi_currency(openingCash, True, cashbox['journal_id'])

    def _post_statement_difference_multi_currency(self, amount, is_opening, journal_id):
        if amount:
            journal_id = self.env['account.journal'].browse(journal_id)

            if self.config_id.cash_control:
                st_line_vals = {
                    'journal_id': journal_id.id,
                    'amount': amount,
                    'date': self.statement_line_ids.sorted()[-1:].date or fields.Date.context_today(self),
                    'pos_session_id': self.id,
                }

            if amount < 0.0:
                if not journal_id.loss_account_id:
                    raise UserError(
                        _('Please go on the %s journal and define a Loss Account. This account will be used to record cash difference.',
                          journal_id.name))

                st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Loss)") + (_(' - opening') if is_opening else _(' - closing'))
                st_line_vals['counterpart_account_id'] = journal_id.loss_account_id.id
            else:
                # self.cash_register_difference  > 0.0
                if not journal_id.profit_account_id:
                    raise UserError(
                        _('Please go on the %s journal and define a Profit Account. This account will be used to record cash difference.',
                          journal_id.name))

                st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Profit)") + (_(' - opening') if is_opening else _(' - closing'))
                st_line_vals['counterpart_account_id'] = journal_id.profit_account_id.id

            self.env['account.bank.statement.line'].create(st_line_vals)

    def get_opening_control_data(self):
        return {
            'journal_ids': self.payment_method_ids.mapped('journal_id').mapped('id'),
            'currency_ids': self.payment_method_ids.mapped('journal_id').mapped('currency_id').mapped('id'),
        }
