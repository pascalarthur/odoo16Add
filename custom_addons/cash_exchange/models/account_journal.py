from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    location_id = fields.Many2one('stock.location', 'Location')

    def action_open_payment_form(self):
        # Logic to open the standard payment form
        # Pre-fill necessary fields based on the journal selected
        return {
            'name': 'Register Payment',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.journal.currency.exchange',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_journal_id': self.id,
                'default_location_id': self.location_id.id,
                # Add other default fields if necessary
            }
        }


class AccountMove(models.Model):
    _inherit = 'account.move'

    def create_currency_conversion_journal_entry(self, source_journal_id, dest_journal_id, amount, date, exchange_rate, memo):
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
            'name': 'CEXCH/' + str(self.env['account.move'].search_count([('name', 'like', 'CEXCH/%')])),
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
            'name': 'CEXCH/' + str(self.env['account.move'].search_count([('name', 'like', 'CEXCH/%')])),
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