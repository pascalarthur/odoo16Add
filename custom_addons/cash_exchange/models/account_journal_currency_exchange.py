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
        self.move_id = self.create_accounting_entry()

    def create_accounting_entry(self):
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line']
        move_id = AccountMove.create({
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.note,
            'currency_id': self.currency_id.id,
        })

        account_move_line_vals = {
            'move_id': move_id.id,
            'journal_id': self.journal_id.id,
            'account_id': self.journal_id.default_account_id.id,
            'name': self.note,
            'currency_id': self.currency_id.id,
            'amount_currency': self.amount,
            'date_maturity': self.date,
            'debit': 0.0,
            'credit': self.amount,
        }

        account_move_line_destination_vals = {
            'move_id': move_id.id,
            'journal_id': self.destination_journal_id.id,
            'account_id': self.destination_journal_id.default_account_id.id,
            'name': self.note,
            'currency_id': self.destination_currency_id.id,
            'amount_currency': self.amount * self.exchange_rate,
            'date_maturity': self.date,
            'debit': self.amount * self.exchange_rate,
            'credit': 0.0,
        }

        move_line_ids = AccountMoveLine.create([account_move_line_vals, account_move_line_destination_vals])

        print(move_line_ids)

        move_id.post()
        self.account_move_id = move_id
        # self.account_move_line_id = account_move_line_id
        # self.account_move_line_destination_id = account_move_line_destination_id
        return move_id.id