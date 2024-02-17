from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    detailed_type = fields.Selection(selection_add=[
        ('product', 'Storable Product'),
        ('transport', 'Transport'),
    ], tracking=True, ondelete={
        'product': 'set consu',
        'transport': 'set consu'
    }, default='product')
    type = fields.Selection(selection_add=[
        ('product', 'Storable Product'),
        ('transport', 'Transport'),
    ], ondelete={
        'product': 'set consu',
        'transport': 'set consu'
    }, default='product')

    start_warehouse_id = fields.Many2one('stock.warehouse', string='Start Warehouse')
    destination_warehouse_id = fields.Many2one('stock.warehouse', string='Destination Warehouse')

    box_weight = fields.Float(string='Box Weight [kg]')
