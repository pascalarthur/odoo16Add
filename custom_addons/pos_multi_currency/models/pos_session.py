from odoo import models, fields, api, _


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()

        currencies = self.env['res.currency'].search_read(
            domain=[('id', 'in', self.config_id.pos_currencies.ids)],
            fields=['name', 'symbol', 'position', 'rounding', 'rate', 'rate'],
        )
        loaded_data['currency_rates'] = currencies
        return loaded_data
