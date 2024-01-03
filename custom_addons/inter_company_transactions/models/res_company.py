from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    enable_inter_company_transactions = fields.Boolean(string="Enable Inter-Company Transactions", default=False)


    def init(self):
        print(self.enable_inter_company_transactions)
        sup = super(ResCompany, self).init()