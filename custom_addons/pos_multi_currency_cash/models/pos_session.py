from typing import List
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PosSession(models.Model):
    _inherit = 'pos.session'

    def correct_cash_amounts(self, cash_amounts_in_currencies):

        print('correct_cash_amounts', cash_amounts_in_currencies)
        print('correct_cash_amounts', self.env['account.move.line'].search([('move_id', '=', self.move_id.id)]))

        journal_ids = self.env['account.journal'].search_read(
			domain=[('id', 'in', self.config_id.currency_journal_ids.ids)],
			fields=['id', 'name', 'currency_id'],
		)
        print('correct_cash_amounts', journal_ids)

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


    def load_pos_data(self):
        loaded_data = super(PosSession, self).load_pos_data()

        for ii in range(len(loaded_data["pos.payment.method"])):
            pm = loaded_data["pos.payment.method"][ii]
            pm_complete = self.env['pos.payment.method'].search([('id', '=', pm['id'])])
            loaded_data["pos.payment.method"][ii]['currency_id'] = pm_complete.journal_id.currency_id.id
            loaded_data["pos.payment.method"][ii]['currency_rate'] = pm_complete.journal_id.currency_id.rate

        currencies = self.env['res.currency'].search_read(
			domain=[('active', '=', True)],
			fields=['name','symbol','position','rounding','rate','rate'],
		)
        loaded_data['currencies'] = currencies

        return loaded_data