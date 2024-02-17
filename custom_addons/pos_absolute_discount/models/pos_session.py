from odoo import models, fields, api, _


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        loaded_data['use_absolute_discount'] = self.config_id.use_absolute_discount
        return loaded_data
