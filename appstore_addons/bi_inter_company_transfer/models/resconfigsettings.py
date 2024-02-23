from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    intercompany_warehouse_id = fields.Many2one('stock.warehouse', string="Intercompany Warehouse")
    allow_auto_intercompany = fields.Boolean('Allow Auto Intercompany Transaction')
    validate_picking = fields.Boolean('Validate Receipt/picking in so/po')
    create_invoice = fields.Boolean('Create Invoice/Bill in so/po')
    validate_invoice = fields.Boolean('Validate Invoice/Bill in so/po')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_auto_intercompany = fields.Boolean('Allow Auto Intercompany Transaction',
                                             related="company_id.allow_auto_intercompany", readonly=False)
    validate_picking = fields.Boolean('Validate Receipt/picking in so/po', related="company_id.validate_picking",
                                      readonly=False)
    create_invoice = fields.Boolean('Create Invoice/Bill in so/po', related="company_id.create_invoice", readonly=False)
    validate_invoice = fields.Boolean('Validate Invoice/Bill in so/po', related="company_id.validate_invoice",
                                      readonly=False)

    # @api.model
    # def get_values(self):
    #     res = super(ResConfigSettings, self).get_values()

    #     res.update(validate_picking=self.env['ir.config_parameter'].sudo().get_param(
    #         'bi_inter_company_transfer.validate_picking'))
    #     res.update(
    #         create_invoice=self.env['ir.config_parameter'].sudo().get_param('bi_inter_company_transfer.create_invoice'))
    #     res.update(validate_invoice=self.env['ir.config_parameter'].sudo().get_param(
    #         'bi_inter_company_transfer.validate_invoice'))
    #     res.update(allow_auto_intercompany=self.env['ir.config_parameter'].sudo().get_param(
    #         'bi_inter_company_transfer.allow_auto_intercompany'))
    #     return res

    # def set_values(self):
    #     super(ResConfigSettings, self).set_values()

    #     self.env['ir.config_parameter'].sudo().set_param('bi_inter_company_transfer.validate_picking',
    #                                                      self.validate_picking)
    #     self.env['ir.config_parameter'].sudo().set_param('bi_inter_company_transfer.create_invoice',
    #                                                      self.create_invoice)
    #     self.env['ir.config_parameter'].sudo().set_param('bi_inter_company_transfer.validate_invoice',
    #                                                      self.validate_invoice)
    #     self.env['ir.config_parameter'].sudo().set_param('bi_inter_company_transfer.allow_auto_intercompany',
    #                                                      self.allow_auto_intercompany)
