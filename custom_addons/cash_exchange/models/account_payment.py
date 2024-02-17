from odoo import api, models, fields
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    available_destination_journal_ids = fields.Many2many('account.journal')
    foreign_currency_id = fields.Many2one('res.currency', string="Foreign Currency",
                                          compute='_compute_foreign_currency_id', store=True, readonly=False,
                                          precompute=True)

    amount_converted = fields.Monetary(string='Amount Converted', currency_field="foreign_currency_id", store=True,
                                       readonly=True, compute='_compute_amount_converted')

    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')
    manual_currency_rate = fields.Float('Rate', digits=(12, 6), default=1.0)

    @api.depends('amount', 'manual_currency_rate')
    def _compute_amount_converted(self):
        for record in self:
            if record.manual_currency_rate > 0:
                record.amount_converted = record.amount * record.manual_currency_rate
            else:
                record.amount_converted = 0.0

    @api.depends('journal_id', 'destination_journal_id')
    def _compute_currency_id(self):
        for pay in self:
            if pay.company_id.currency_id.id == pay.journal_id.currency_id.id:
                pay.currency_id = pay.destination_journal_id.currency_id
            else:
                pay.currency_id = pay.journal_id.currency_id

    @api.depends('journal_id', 'destination_journal_id')
    def _compute_foreign_currency_id(self):
        for pay in self:
            if pay.company_id.currency_id.id == pay.journal_id.currency_id.id:
                pay.foreign_currency_id = pay.journal_id.currency_id
            else:
                pay.foreign_currency_id = pay.destination_journal_id.currency_id

    @api.model
    def auto_reconcile(self):
        self.ensure_one()

        vals = {
            "journal_id": self.journal_id.id,
            "amount": self.amount_company_currency_signed,
            "date": self.date,
            "company_id": self.company_id.id,
            "partner_id": self.partner_id.id,
            "ref": self.display_name,
        }

        if self.company_id.currency_id.id != self.journal_id.currency_id.id:
            vals["amount"] = self.amount_signed
            vals["amount_currency"] = self.amount_company_currency_signed
            vals["foreign_currency_id"] = self.company_id.currency_id.id

        statement_line_id = self.env["account.bank.statement.line"].create([vals])

        statement_line_id.matched_payment_ids = self
        statement_line_id.action_reconcile()

    def action_post(self):
        self.ensure_one()
        if self.is_internal_transfer:
            if self.journal_id.currency_id.id != self.destination_journal_id.currency_id.id:
                if self.company_id.currency_id.id not in [
                        self.journal_id.currency_id.id, self.destination_journal_id.currency_id.id
                ]:
                    raise UserError("One of the currencies must be in the company currency.")
                if self.currency_id.id == self.company_id.currency_id.id:
                    raise UserError("The currency of the payment must be different from the currency of the company.")
        super(AccountPayment, self).action_post()

    def action_custom_post(self):
        super(AccountPayment, self).action_post()
        self.auto_reconcile()
        self.paired_internal_transfer_payment_id.auto_reconcile()

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional list of dictionaries to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or {}

        if not self.outstanding_account_id:
            raise UserError(
                _(
                    "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
                    self.payment_method_line_id.name, self.journal_id.display_name))

        # Compute amounts.
        write_off_line_vals_list = write_off_line_vals or []
        write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
        write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
        else:
            liquidity_amount_currency = 0.0

        # CHANGES HERE: Use different currency and rate if manual currency rate is active
        if self.manual_currency_rate_active:
            liquidity_balance = liquidity_amount_currency
            if self.currency_id.id != self.company_id.currency_id.id:
                liquidity_balance *= self.manual_currency_rate
        else:
            liquidity_balance = self.currency_id._convert(
                liquidity_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
        counterpart_balance = -liquidity_balance - write_off_balance
        currency_id = self.currency_id.id

        # Compute a default label to set on the journal items.
        liquidity_line_name = ''.join(x[1] for x in self._get_liquidity_aml_display_name_list())
        counterpart_line_name = ''.join(x[1] for x in self._get_counterpart_aml_display_name_list())

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.outstanding_account_id.id,
            },
            # Receivable / Payable.
            {
                'name': counterpart_line_name,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
            },
        ]
        return line_vals_list + write_off_line_vals_list
