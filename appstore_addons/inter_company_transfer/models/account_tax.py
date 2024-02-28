from odoo import models, _


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def map_tax_ids(self, company) -> list:
        taxes_return = self.env['account.tax']
        for tax in self:
            taxes_return += self.env['account.tax'].search([('company_id', '=', company.id), ('name', '=', tax.name)])
        return taxes_return
