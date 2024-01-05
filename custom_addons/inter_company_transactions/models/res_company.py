from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    enable_inter_company_transactions = fields.Boolean(string="Enable Inter-Company Transactions", default=False)
    inter_company_partner_ids = fields.Many2many(
        'res.company',
        'company_inter_company_rel',
        'company_id',
        'partner_company_id',
        string='Inter-Company Partners',
        domain="[('id', '!=', company_id)]"
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_inter_company_transactions = fields.Boolean(
        string="Enable Inter-Company Transactions",
        related='company_id.enable_inter_company_transactions',
        readonly=False
    )

    inter_company_partner_ids = fields.Many2many(
        related='company_id.inter_company_partner_ids',
        string='Inter-Company Partners',
        readonly=False
    )

    