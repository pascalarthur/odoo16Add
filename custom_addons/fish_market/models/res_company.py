from odoo import models, fields, api
from markupsafe import Markup


class Company(models.Model):
    _inherit = "res.company"

    report_footer = fields.Html(string='Report Footer', translate=True, readonly=True, compute='_compute_invoice_footer')

    @api.depends('phone', 'email', 'website', 'vat')
    def _compute_invoice_footer(self):
        for company in self:
            footer_fields = [field for field in [company.phone, company.email, company.website, company.vat] if isinstance(field, str) and len(field) > 0]
            company.report_footer = Markup(' ').join(footer_fields)