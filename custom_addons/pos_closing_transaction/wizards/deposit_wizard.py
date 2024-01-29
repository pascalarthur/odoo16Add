from odoo import models, fields, api, _
from odoo.exceptions import UserError

class YourWizard(models.TransientModel):
    _name = 'deposit.wizard'

    currency_id = fields.Many2one('res.currency', string='Currency')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    amount_left = fields.Monetary(string='Amount Left', currency_field='currency_id', compute='_compute_amount_left', readonly=True)
    pos_config = fields.Many2one('pos.config', string='POS Config')
    pos_session = fields.Many2one('pos.session', string='POS Session')

    def record_transaction(self):
        if self.pos_config.last_session_closing_cash < self.amount:
            raise UserError(_('You cannot deposit more than the amount left in the cash register'))
        else:
            self.pos_config.last_session_closing_cash -= self.amount
            self.pos_session.cash_register_balance_end_real -= self.amount

    @api.onchange('amount')
    def _compute_amount_left(self):
        self.amount_left = self.pos_config.last_session_closing_cash - self.amount