from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def deposit_money_in_safe(self):
        session = self.env['pos.session'].search([('config_id', '=', self.id), ('state', '=', 'closed')],
                                                 order="stop_at desc", limit=1)

        return {
            'name': 'Deposit Money',
            'type': 'ir.actions.act_window',
            'res_model': 'deposit.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_pos_config': self.id,
                'default_pos_session': session[0].id,
                'default_currency_id': session[0].cash_journal_id.currency_id.id,
            }
        }
