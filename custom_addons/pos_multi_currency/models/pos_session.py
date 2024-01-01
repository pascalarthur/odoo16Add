from odoo import models, fields, api

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