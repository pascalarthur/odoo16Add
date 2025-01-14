from typing import List
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PosSession(models.Model):
    _inherit = 'pos.session'

    def correct_cash_amounts_opening(self, cash_amounts_in_currencies: List[dict]):
        # Find the cash payment method in the POS configuration
        cash_payment_method = self.config_id.payment_method_ids.filtered(lambda pm: pm.is_cash_count and pm.journal_id)

        if not cash_payment_method:
            raise UserError("No cash payment method found in the POS configuration.")

        # Get the default journal and currency from the cash payment method
        default_journal_id = cash_payment_method.journal_id.id
        default_currency_id = cash_payment_method.journal_id.currency_id.id or cash_payment_method.journal_id.company_id.currency_id.id

        # Filter out the default currency from the list of cash amounts
        default_cash = next(cash for cash in cash_amounts_in_currencies if cash['journal_id'] == default_journal_id)

        for cash in cash_amounts_in_currencies:
            # Skip if the currency is already the default POS currency
            if cash['id'] == default_currency_id or cash['counted'] == 0:
                continue

            cash_id = self.env["res.currency"].browse(cash["id"])
            default_cash_id = self.env["res.currency"].browse(default_cash["id"])

            exchange_rate = self.env["res.currency"]._get_conversion_rate(default_cash_id, cash_id)
            # Create an AccountJournalCurrencyExchange record
            exchange_vals = {
                'is_internal_transfer': True,
                'payment_type': 'outbound',
                'journal_id': cash['journal_id'],
                'destination_journal_id': default_journal_id,
                'amount': cash['counted'],
                'manual_currency_rate_active': True,
                'manual_currency_rate': 1 / exchange_rate,
                'date': fields.Date.today(),
                'ref': f"Exchange from default POS currency to {cash['name']}",
            }

            # The payment is always in the currency that is not equal to the company currency
            if cash['id'] == self.company_id.currency_id.id:
                exchange_vals['manual_currency_rate'] = exchange_rate
                exchange_vals['amount'] /= exchange_rate

            exchange_record = self.env['account.payment'].create(exchange_vals)
            exchange_record.action_post()

    def correct_cash_amounts_closing(self, cash_amounts_in_currencies: List[dict]):
        # print('correct_cash_amounts_closing', 'location_id', self.config_id.location_id.id)

        # Find the cash payment method in the POS configuration
        cash_payment_method = self.config_id.payment_method_ids.filtered(lambda pm: pm.is_cash_count and pm.journal_id)

        if not cash_payment_method:
            raise UserError("No cash payment method found in the POS configuration.")

        # Get the default journal and currency from the cash payment method
        default_journal_id = cash_payment_method.journal_id.id
        default_currency_id = cash_payment_method.journal_id.currency_id.id or cash_payment_method.journal_id.company_id.currency_id.id

        # Filter out the default currency from the list of cash amounts
        default_cash = next(cash for cash in cash_amounts_in_currencies if cash['journal_id'] == default_journal_id)

        for cash in cash_amounts_in_currencies:
            # Skip if the currency is already the default POS currency
            if cash['id'] == default_currency_id or cash['counted'] == 0:
                continue

            cash_id = self.env["res.currency"].browse(cash["id"])
            default_cash_id = self.env["res.currency"].browse(default_cash["id"])

            exchange_rate = self.env["res.currency"]._get_conversion_rate(default_cash_id, cash_id)

            # Create an AccountJournalCurrencyExchange record
            exchange_vals = {
                'is_internal_transfer': True,
                'payment_type': 'outbound',
                'journal_id': default_journal_id,
                'destination_journal_id': cash['journal_id'],
                'amount': cash['counted'],
                'manual_currency_rate_active': True,
                'manual_currency_rate': 1 / exchange_rate,
                'date': fields.Date.today(),
                'ref': f"Exchange from {cash['name']} to default POS currency",
            }

            # The payment is always in the currency that is not equal to the company currency
            if cash['id'] == self.company_id.currency_id.id:
                exchange_vals['manual_currency_rate'] = exchange_rate
                exchange_vals['amount'] /= exchange_rate

            exchange_record = self.env['account.payment'].create(exchange_vals)
            exchange_record.action_post()

    def get_available_product_quantities(self):
        available_product_quantities = {}
        for product in self.config_id.available_product_ids:
            stocked_products = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id', '=', self.config_id.picking_type_id.default_location_src_id.id), ('quantity', '>', 0)
            ])
            available_product_quantities[product.id] = sum(stocked_products.mapped('quantity'))

        return available_product_quantities

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()

        for ii in range(len(loaded_data["pos.payment.method"])):
            pm = loaded_data["pos.payment.method"][ii]
            pm_complete = self.env['pos.payment.method'].search([('id', '=', pm['id'])])
            loaded_data["pos.payment.method"][ii]['currency_id'] = pm_complete.journal_id.currency_id.id
            loaded_data["pos.payment.method"][ii]['currency_rate'] = pm_complete.journal_id.currency_id.inverse_rate

        journal_ids = self.env['account.journal'].sudo().search(
            domain=[('id', 'in', self.config_id.currency_journal_ids.ids)], )

        currencies = []
        for journal_id in journal_ids:
            currencies.append({
                'id': journal_id.currency_id.id,
                'name': journal_id.currency_id.name,
                'symbol': journal_id.currency_id.symbol,
                'position': journal_id.currency_id.position,
                'rounding': journal_id.currency_id.rounding,
                'rate': journal_id.currency_id.inverse_rate,
                'journal_id': journal_id.id,
                'counted': 0,
            })

        loaded_data['currencies'] = currencies
        return loaded_data
