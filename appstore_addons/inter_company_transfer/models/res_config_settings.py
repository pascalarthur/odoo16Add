from odoo import fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    intercompany_warehouse_id = fields.Many2one('stock.warehouse', string="Intercompany Warehouse")
    allow_intercompany_transactions = fields.Boolean('Enable Intercompany Transaction')
    validate_picking = fields.Boolean('Validate Receipt/picking in so/po')
    create_invoice = fields.Boolean('Create Invoice/Bill in so/po')
    validate_invoice = fields.Boolean('Validate Invoice/Bill in so/po')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_intercompany_transactions = fields.Boolean('Enable Intercompany Transaction',
                                                     related="company_id.allow_intercompany_transactions",
                                                     readonly=False)
    validate_picking = fields.Boolean('Validate Receipt/picking in so/po', related="company_id.validate_picking",
                                      readonly=False)
    create_invoice = fields.Boolean('Create Invoice/Bill in so/po', related="company_id.create_invoice", readonly=False)
    validate_invoice = fields.Boolean('Validate Invoice/Bill in so/po', related="company_id.validate_invoice",
                                      readonly=False)
