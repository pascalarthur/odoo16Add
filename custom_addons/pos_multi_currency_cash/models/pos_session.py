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

    @api.depends('payment_method_ids', 'order_ids', 'cash_register_balance_start')
    def _compute_cash_balance(self):
        for session in self:
            cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[:1]
            if cash_payment_method:
                total_cash_payment = 0.0
                last_session = session.search([('config_id', '=', session.config_id.id), ('id', '<', session.id)], limit=1)
                result = self.env['pos.payment']._read_group([('session_id', '=', session.id), ('payment_method_id', '=', cash_payment_method.id)], aggregates=['amount:sum'])
                total_cash_payment = result[0][0] or 0.0
                if session.state == 'closed':
                    session.cash_register_total_entry_encoding = session.cash_real_transaction + total_cash_payment
                else:
                    session.cash_register_total_entry_encoding = sum(session.statement_line_ids.filtered(lambda pm: pm.journal_id == cash_payment_method.journal_id).mapped('amount')) + total_cash_payment

                session.cash_register_balance_end = last_session.cash_register_balance_end_real + session.cash_register_total_entry_encoding
                session.cash_register_difference = session.cash_register_balance_end_real - session.cash_register_balance_end
                print('_compute_cash_balance 2', session.cash_register_balance_end, session.cash_register_difference)
            else:
                session.cash_register_total_entry_encoding = 0.0
                session.cash_register_balance_end = 0.0
                session.cash_register_difference = 0.0

    def get_opening_control_data(self):
        cash_payment_method_ids = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
        default_cash_payment_method_id = cash_payment_method_ids[0] if cash_payment_method_ids else None
        other_payment_method_ids = self.payment_method_ids - default_cash_payment_method_id if default_cash_payment_method_id else self.payment_method_ids

        return {'other_payment_methods': [{
                'name': pm.name,
                'journal_id': pm.journal_id.id,
                'currency_id': pm.journal_id.currency_id.id,
                'currency_name': pm.journal_id.currency_id.name,

                'id': pm.id,
                'type': pm.type,
            } for pm in other_payment_method_ids],
        }

    def get_closing_control_data(self):
        closing_control_data = super(PosSession, self).get_closing_control_data()
        orders = self._get_closed_orders()
        payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
        cash_payment_method_ids = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
        default_cash_payment_method_id = cash_payment_method_ids[0] if cash_payment_method_ids else None
        total_default_cash_payment_amount = sum(payments.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id).mapped('amount')) if default_cash_payment_method_id else 0
        other_payment_method_ids = self.payment_method_ids - default_cash_payment_method_id if default_cash_payment_method_id else self.payment_method_ids

        last_session = self.search([('config_id', '=', self.config_id.id), ('id', '!=', self.id)], limit=1)

        closing_control_data['default_cash_details']['amount'] = last_session.cash_register_balance_end_real + \
            total_default_cash_payment_amount + \
                sum(self.sudo().statement_line_ids.filtered(lambda p: p.journal_id == default_cash_payment_method_id.journal_id).mapped('amount'))

        for ii, pm in enumerate(other_payment_method_ids):
            closing_control_data['other_payment_methods'][ii]['amount'] += sum(self.sudo().statement_line_ids.filtered(lambda p: p.journal_id == pm.journal_id).mapped('amount'))

        return closing_control_data
