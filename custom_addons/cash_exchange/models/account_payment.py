from odoo import api, models, fields

class AccountPayment(models.Model):
    _inherit = "account.payment"

    available_destination_journal_ids = fields.Many2many('account.journal')

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
        # else:
        #     if self.company_id.currency_id.id != self.destination_journal_id.currency_id.id:
        #         vals["amount_currency"] = self.amount_company_currency_signed
        #         vals["foreign_currency_id"] = self.company_id.currency_id.id


        statement_line_id = self.env["account.bank.statement.line"].create([vals])

        statement_line_id.matched_payment_ids = self
        statement_line_id.action_reconcile()

    def action_post(self):
        super(AccountPayment, self).action_post()

    def action_custom_post(self):
        super(AccountPayment, self).action_post()
        self.auto_reconcile()
        self.paired_internal_transfer_payment_id.auto_reconcile()
