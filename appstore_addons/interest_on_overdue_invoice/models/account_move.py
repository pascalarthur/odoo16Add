from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import formatLang

old_domain = [('display_type', 'in', ('product', 'line_section', 'line_note'))]
new_domain = old_domain + [('interest_line', '=', False)]


class account_payment_term(models.Model):
    _inherit = "account.payment.term"

    interest_type = fields.Selection([
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
    ], 'Interest Type')
    interest_percentage = fields.Float('Interest Percentage', digits=(16, 6))
    account_id = fields.Many2one('account.account', 'Account')


class account_move_line(models.Model):
    _inherit = 'account.move.line'

    interest_line = fields.Boolean('Is Interest Line')


class account_invoice(models.Model):
    _inherit = "account.move"

    invoice_line_ids = fields.One2many('account.move.line', 'move_id', string='Invoice lines', copy=False,
                                       readonly=True, domain=new_domain)
    interest_account_move_line = fields.Many2one(
        'account.move.line',
        string='Interest Account Move Line',
    )
    show_intrest = fields.Boolean('is_intrest', default=False, copy=False)
    interest = fields.Float(string="Interest", readonly=True, copy=False)
    interest_company_currency = fields.Float(string="Company Currency Interest", readonly=True, copy=False)
    no_overtime_periods = fields.Integer(string='No. of Overtime Periods', copy=False)

    @api.model_create_multi
    def create(self, vals):
        res = super(account_invoice, self).create(vals)
        res._onchange_date_due()
        return res

    @api.onchange('interest', 'interest_company_currency')
    def _onchange_interest_company_currency(self):
        self.interest_company_currency = self.currency_id._convert(self.interest, self.company_id.currency_id,
                                                                   self.company_id, self.invoice_date)

    @api.onchange('invoice_date_due', 'invoice_date', 'invoice_line_ids')
    def _onchange_date_due(self):
        if self.invoice_date_due and self.invoice_date:
            self.show_intrest = self.invoice_date < self.invoice_date_due
        if self.invoice_line_ids:
            self.show_intrest = True

    @api.depends('invoice_line_ids.currency_rate', 'invoice_line_ids.tax_base_amount', 'invoice_line_ids.tax_line_id',
                 'invoice_line_ids.price_total', 'invoice_line_ids.price_subtotal', 'invoice_payment_term_id',
                 'partner_id', 'currency_id', 'interest')
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        self._onchange_interest_company_currency()
        for record in self:
            tax_totals = record.tax_totals
            if tax_totals and tax_totals.get('amount_total'):
                tax_totals['amount_total'] = tax_totals['amount_total'] + record.interest
                if tax_totals.get('formatted_amount_total'):
                    tax_totals['formatted_amount_total'] = formatLang(self.env, tax_totals['amount_total'],
                                                                      currency_obj=record.currency_id)
                record.update({'tax_totals': tax_totals})

    @api.depends('invoice_line_ids.price_subtotal', 'currency_id', 'company_id', 'invoice_date', 'discount_type', '')
    def _compute_interest_amount(self):
        if self.move_type == 'out_invoice':
            if self.invoice_payment_term_id.interest_type not in ['daily', 'monthly']:
                self.update({'interest': 0.0})
            elif self.invoice_date_due and self.invoice_payment_term_id:
                maturity_in_days = (fields.Date.today() - self.invoice_date_due).days
                maturity_in_years = relativedelta(fields.Date.today(), self.invoice_date_due).years
                maturity_in_months = maturity_in_years * 12 + relativedelta(fields.Date.today(),
                                                                            self.invoice_date_due).months
                if maturity_in_days > 0:
                    self.show_intrest = True
                    if self.invoice_payment_term_id.interest_type == 'daily':
                        no_overtime_periods = maturity_in_days
                    elif self.invoice_payment_term_id.interest_type == 'monthly':
                        no_overtime_periods = maturity_in_months

                    int_per = (self.amount_untaxed + self.amount_tax) * (
                        self.invoice_payment_term_id.interest_percentage / 100) * (no_overtime_periods)
                    self.update({
                        'interest': int_per,
                        'amount_total': int_per,
                        'no_overtime_periods': no_overtime_periods
                    })
                    self._check_interest_date_update_move_line()

    def _check_interest_date_update_move_line(self):
        self.line_ids -= self.interest_account_move_line
        self.interest_account_move_line.with_context(check_move_validity=False).unlink()
        vals = {
            'name': 'Interest Entry',
            'move_id': self.id,
            'price_unit': self.interest,
            'account_id': self.invoice_payment_term_id.account_id.id,
            'amount_currency': -self.interest,
            'interest_line': True,
            'quantity': 1,
        }
        self.interest_account_move_line = self.env['account.move.line'].create(vals)
        self.line_ids += self.interest_account_move_line

    @api.model
    def cron_interest(self):
        res = self.env['account.move'].search([('payment_state', 'in', ['not_paid', 'in_payment'])])
        for record in res:
            if record.state == 'draft':
                record.button_add_interest()
            elif record.state == 'posted':
                record.action_interest_update_cancel()

    def button_add_interest(self):
        self._compute_interest_amount()
        self._compute_tax_totals()

    def button_reset_interest(self):
        self.update({'interest': 0.0})
        self.line_ids -= self.interest_account_move_line
        self.interest_account_move_line.with_context(check_move_validity=False).unlink()
        self._compute_tax_totals()

    def action_interest_update_cancel(self):
        self.button_draft()
        self.button_add_interest()
        self.action_post()
