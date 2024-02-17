from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'
    invoice_auto_check = fields.Boolean()


class ResConfig(models.TransientModel):
    _inherit = 'res.config.settings'
    invoice_auto_check = fields.Boolean(related="pos_config_id.invoice_auto_check", readonly=False)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()
        loaded_data['invoice_auto_check'] = self.config_id.invoice_auto_check
        return loaded_data
