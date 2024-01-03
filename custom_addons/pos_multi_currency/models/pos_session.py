from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        currencies = self.env['res.currency'].search_read(
			domain=[('active', '=', True)],
			fields=['name','symbol','position','rounding','rate','exchange_rate'],
		)
        print('load_pos_data', currencies)
        loaded_data['currencies'] = currencies
        return loaded_data
