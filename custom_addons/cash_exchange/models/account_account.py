from odoo import _, fields, models
from odoo.exceptions import UserError
from ..utils.model_utils import default_name


class AccountAccount(models.Model):
    _inherit = 'account.account'

    location_id = fields.Many2one('stock.location', 'Location')

    current_balance_currency = fields.Monetary(
        string='Current Balance (Currency)',
        store=False,
        compute='_compute_current_balance_currency',
        currency_field='currency_id',
    )

    def _compute_current_balance_currency(self):
        for account in self:
            account.current_balance_currency = sum(self.env['account.move.line'].search([('account_id', '=', account.id)
                                                                                         ]).mapped('amount_currency'))

    def action_open_payment_form(self):
        available_journal_ids = self.env['account.journal'].search([
            ('type', 'in', ['bank', 'cash']),
            ('currency_id', '=', self.currency_id.id),
            ('company_id', '=', self.env.company.id),
            ('default_account_id', '=', self.id),
        ]).ids

        available_destination_journal_ids = self.env['account.journal'].search([
            ('type', 'in', ['bank', 'cash']),
            ('company_id', '=', self.env.company.id),
            ('default_account_id', '!=', self.id),
        ]).ids

        return {
            'name': 'Register Payment',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'views': [(self.env.ref("cash_exchange.view_exchange_payment_form").id, 'form')],
            'target': 'new',
            'context': {
                'default_is_internal_transfer': True,
                'default_payment_type': 'outbound',
                'default_manual_currency_rate_active': True,
                'default_account_id': self.id,
                'default_location_id': self.location_id.id,
                'default_journal_id': available_journal_ids[0] if available_journal_ids else False,
                'default_available_journal_ids': available_journal_ids,
                'default_available_destination_journal_ids': available_destination_journal_ids,
            }
        }


class AccountMove(models.Model):
    _inherit = 'account.move'

    def create_currency_conversion_journal_entry(self, source_journal_id, dest_journal_id, amount, date, exchange_rate,
                                                 memo):
        """
        Create a journal entry to convert currency from one journal to another.

        :param source_journal_id: ID of the source journal
        :param dest_journal_id: ID of the destination journal
        :param amount: Amount to transfer
        :param date: Date of the transaction
        :param memo: Memo for the journal entry
        """
        source_journal = self.env['account.journal'].browse(source_journal_id)
        dest_journal = self.env['account.journal'].browse(dest_journal_id)

        if source_journal.currency_id == dest_journal.currency_id:
            raise UserError("Both journals have the same currency.")

        # Calculate converted amount based on exchange rates
        converted_amount = amount * exchange_rate

        print('create_currency_conversion_journal_entry', amount, exchange_rate, converted_amount)

        # Create journal entry
        move_vals_outgoing = {
            'name': default_name(self, prefix='CEXCH/'),
            'journal_id': source_journal_id,
            'date': date,
        }
        move_outgoing = self.create(move_vals_outgoing)
        self.env['account.bank.statement.line'].create({
            'date': date,
            'name': memo or '/',
            'amount': -amount,
            'journal_id': source_journal_id,
            'move_id': move_outgoing.id,
        })

        move_vals_incoming = {
            'name': default_name(self, prefix='CEXCH/'),
            'journal_id': dest_journal_id,
            'date': date,
        }
        move_incoming = self.create(move_vals_incoming)

        self.env['account.bank.statement.line'].create({
            'date': date,
            'name': memo or '/',
            'amount': converted_amount,
            'journal_id': dest_journal_id,
            'move_id': move_incoming.id,
        })

        if self.state != 'posted':
            self.post()

        return move_incoming
