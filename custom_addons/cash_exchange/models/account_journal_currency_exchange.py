from odoo import _, fields, models


class AccountJournalCurrencyExchange(models.Model):
    _name = 'account.journal.currency.exchange'

    location_id = fields.Many2one('stock.location', 'Location')
    exchange_partner_id = fields.Many2one('res.partner', string='Exchange Partner')

    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    destination_journal_id = fields.Many2one('account.journal', string='Destination Journal', required=True)
    amount = fields.Monetary(string='Amount', required=True)
    exchange_rate = fields.Float(string='Exchange Rate', required=True)
    currency_id = fields.Many2one('res.currency', related='journal_id.currency_id', string='Currency', readonly=True)
    destination_currency_id = fields.Many2one('res.currency', related='destination_journal_id.currency_id', string='Destination Currency', readonly=True)

    date = fields.Date(string='Date', required=True, default=fields.Date.today())
    note = fields.Char(string='Note')

    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancel')], string='Status', default='draft')

    account_move_line_id = fields.Many2one('account.move.line', string='Account Move', readonly=True)
    account_move_line_destination_id = fields.Many2one('account.move.line', string='Account Move Destination', readonly=True)
    account_move_id = fields.Many2one('account.move', string='Account Move', readonly=True)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_cancel(self):
        self.state = 'cancel'

    def action_done(self):
        self.state = 'done'
        return self.create_accounting_entry()

    def create_accounting_entry(self):
        AccountMove = self.env['account.move']
        move_id = AccountMove.create_currency_conversion_journal_entry(source_journal_id=self.journal_id.id, dest_journal_id=self.destination_journal_id.id, amount=self.amount, date=self.date, memo='')
        if move_id.state != 'posted':
            move_id.post()
        # return move_id.action_register_payment()
