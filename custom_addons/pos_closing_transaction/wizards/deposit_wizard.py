from odoo import models, fields, api, _
from odoo.exceptions import UserError


class YourWizard(models.TransientModel):
    _name = 'deposit.wizard'

    # Prefilled in models/pos_config.py
    pos_config = fields.Many2one('pos.config', string='POS Config')
    pos_session = fields.Many2one('pos.session', string='POS Session')
    currency_id = fields.Many2one('res.currency', string='Currency')

    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    amount_left = fields.Monetary(string='Amount Left', currency_field='currency_id', compute='_compute_amount_left',
                                  readonly=True)
    destination_journal_id = fields.Many2one('account.journal', string='Destination Journal',
                                             domain="[('currency_id','=',currency_id)]", required=True)
    destination_account_id = fields.Many2one('account.account', string='Destination Account',
                                             related='destination_journal_id.default_account_id', readonly=True)

    @api.onchange('amount')
    def _compute_amount_left(self):
        self.amount_left = self.pos_config.last_session_closing_cash - self.amount

    def record_transaction(self):
        if self.pos_config.last_session_closing_cash < self.amount:
            raise UserError(_('You cannot deposit more than the amount left in the cash register'))

        self.pos_config.last_session_closing_cash -= self.amount
        self.pos_session.cash_register_balance_end_real -= self.amount

        payment_id = self.env['account.payment'].create({
            'is_internal_transfer':
            True,
            'payment_type':
            'outbound',
            'journal_id':
            self.pos_session.cash_journal_id.id,
            'destination_journal_id':
            self.destination_journal_id.id,
            'amount':
            self.amount,
            'currency_id':
            self.currency_id.id,
            'date':
            fields.Date.today(),
            'ref':
            f'POS-Deposit from {self.pos_session.cash_journal_id.name} to {self.destination_journal_id.name}',
        })

        payment_id.action_post_and_reconcile()
