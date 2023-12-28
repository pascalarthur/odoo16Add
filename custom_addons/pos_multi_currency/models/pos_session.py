from odoo import models, fields, api

class PosSession(models.Model):
    _inherit = 'pos.session'

    # # Using Many2many field to store multiple currencies
    alternative_currency_ids = fields.Many2many('res.currency', string="Alternative Currencies", readonly=True)


    def action_pos_session_open(self):
        # we only open sessions that haven't already been opened
        for session in self.filtered(lambda session: session.state == 'opening_control'):
            values = {}
            if not session.start_at:
                values['start_at'] = fields.Datetime.now()
            if session.config_id.cash_control and not session.rescue:
                last_session = self.search([('config_id', '=', session.config_id.id), ('id', '!=', session.id)], limit=1)
                session.cash_register_balance_start = last_session.cash_register_balance_end_real  # defaults to 0 if lastsession is empty
            else:
                values['state'] = 'opened'

            active_currencies = self.env['res.currency'].search([('active', '=', True), ('id', '!=', session.currency_id.id)])
            values['alternative_currency_ids'] = [(6, 0, active_currencies.ids)]

            session.write(values)
            print(session.alternative_currency_ids)
        return True
