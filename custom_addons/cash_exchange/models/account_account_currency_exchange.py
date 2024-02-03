from odoo import api, _, fields, models


# class AccountJournalCurrencyExchange(models.Model):
#     _name = 'account.journal.currency.exchange'

class AccountAccountCurrencyExchange(models.Model):
    _name = 'account.account.currency.exchange'

    location_id = fields.Many2one('stock.location', 'Location')
    exchange_partner_id = fields.Many2one('res.partner', string='Exchange Partner')

    account_id = fields.Many2one('account.account', string='Account', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    interbank_account_id = fields.Many2one('account.account', string='INTERBANK Account', required=True)
    destination_journal_id = fields.Many2one('account.journal', string='Destination Journal', required=True)
    destination_account_id = fields.Many2one('account.account', string='Destination Account', required=True)

    amount = fields.Float(string='Amount', required=True, digits=(16, 7))
    exchange_rate = fields.Float(string='Exchange Rate', required=True, digits=(16, 7))
    currency_id = fields.Many2one('res.currency', related='journal_id.currency_id', string='Currency', readonly=True)
    destination_currency_id = fields.Many2one('res.currency', related='destination_account_id.currency_id', string='Destination Currency', readonly=True)

    date = fields.Date(string='Date', required=True, default=fields.Date.today())
    note = fields.Char(string='Note')

    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancel')], string='Status', default='draft')

    amount_in_other_currency = fields.Monetary(string='Amount Converted', compute='_compute_amount_in_other_currency', store=True, currency_field='destination_currency_id')

    account_move_id = fields.Many2one('account.move', string='Account Move', readonly=True)

    @api.depends('amount', 'exchange_rate')
    def _compute_amount_in_other_currency(self):
        for rec in self:
            rec.amount_in_other_currency = rec.amount * rec.exchange_rate

    def action_confirm(self):
        self.state = 'confirmed'

    def action_cancel(self):
        self.state = 'cancel'

    def action_done(self):
        self.state = 'done'
        return self.create_accounting_entry()

    def create_accounting_entry(self):
        self.env['account.move'].create_currency_conversion_journal_entry(
            source_journal_id=self.journal_id.id,
            dest_journal_id=self.destination_journal_id.id,
            amount=self.amount,
            date=self.date,
            exchange_rate=self.exchange_rate,
            memo=''
        )
