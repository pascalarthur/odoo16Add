from odoo import fields, models


class PaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    interest_type = fields.Selection([('daily', 'Daily'), ('monthly', 'Monthly'), ('yearly', 'Yearly'),
                                      ('penalty', 'Penalty')], string='Interest Type', default='daily', required=True)
    interest_percentage = fields.Float(string='Interest Percentage', default=0.0, required=True)
    interest_account = fields.Many2one('account.account', string='Interest Account', required=True)
