from odoo import api, fields, models, exceptions
from odoo.tools import format_date
from dateutil.relativedelta import relativedelta


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    display_type = fields.Selection(
        selection=[
            ('product', 'Product'),
            ('cogs', 'Cost of Goods Sold'),
            ('tax', 'Tax'),
            ('discount', "Discount"),
            ('rounding', "Rounding"),
            ('payment_term', 'Payment Term'),
            ('line_section', 'Section'),
            ('line_note', 'Note'),
            ('epd', 'Early Payment Discount'),
            ('interest', 'Interest')
        ],
        compute='_compute_display_type', store=True, readonly=False, precompute=True,
        required=True,
    )


class AccountMove(models.Model):
    _inherit = 'account.move'

    interest_overdue_amount = fields.Monetary(string='Interest Overdue Amount')

    def _update_interest_to_journal_items(self):
        self.ensure_one()
        if self.interest_overdue_amount > 0.0:
            interest_account = self.invoice_payment_term_id.interest_account
            if interest_account:
                interest_journal_item = self.line_ids.filtered(lambda x: x.name == 'Interest Overdue')
                if not interest_journal_item:
                    interest_journal_item = self.env['account.move.line'].create({
                        'move_id': self.id,
                        'name': 'Interest Overdue',
                        'account_id': interest_account.id,
                        'currency_id': self.currency_id.id,
                        'amount_currency': -self.interest_overdue_amount,
                        'display_type': 'interest',
                    })
                interest_journal_item.write({
                    'amount_currency': -self.interest_overdue_amount,
                })
                self._compute_amount()
            else:
                raise exceptions.UserError('Please set an interest account in the payment term.')

    @api.depends('line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
                 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
                 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
                 'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
                 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
                 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
                 'line_ids.balance', 'line_ids.currency_id', 'line_ids.amount_currency', 'line_ids.amount_residual',
                 'line_ids.amount_residual_currency', 'line_ids.payment_id.state', 'line_ids.full_reconcile_id',
                 'state')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0

            for line in move.line_ids:
                if move.is_invoice(True):
                    # === Invoices ===
                    if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding', 'interest'):
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == 'payment_term':
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign
            move.amount_untaxed = sign * total_untaxed_currency
            move.amount_tax = sign * total_tax_currency
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(
                move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)

    def compute_interest_overdue_amount(self):
        self.ensure_one()
        self.interest_overdue_amount = 0.0

        maturity_in_days = (fields.Date.today() - self.invoice_date_due).days
        maturity_in_years = relativedelta(fields.Date.today(), self.invoice_date_due).years
        maturity_in_months = maturity_in_years * 12 + relativedelta(fields.Date.today(), self.invoice_date_due).months
        interest = self.invoice_payment_term_id.interest_percentage / 100
        if maturity_in_days > 0:
            if self.invoice_payment_term_id.interest_type == 'penalty':
                self.interest_overdue_amount = 0.0
            elif self.invoice_payment_term_id.interest_type == 'daily':
                self.interest_overdue_amount = interest * self.amount_total * maturity_in_days
            elif self.invoice_payment_term_id.interest_type == 'monthly':
                self.interest_overdue_amount = interest * self.amount_total * maturity_in_months
            elif self.invoice_payment_term_id.interest_type == 'yearly':
                self.interest_overdue_amount = interest * self.amount_total * maturity_in_years

        self._update_interest_to_journal_items()

    def reset_interest_overdue_amount(self):
        self.ensure_one()
        self.interest_overdue_amount = 0.0
        interest_journal_item = self.line_ids.filtered(lambda x: x.name == 'Interest Overdue')
        if interest_journal_item:
            interest_journal_item.unlink()
