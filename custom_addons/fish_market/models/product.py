from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_transport = fields.Boolean(string='Is Transport', default=False)

    start_warehouse_id = fields.Many2one('stock.warehouse', string='Start Warehouse')
    destination_warehouse_id = fields.Many2one('stock.warehouse', string='Destination Warehouse')

    box_weight = fields.Float(string='Box Weight [kg]')
