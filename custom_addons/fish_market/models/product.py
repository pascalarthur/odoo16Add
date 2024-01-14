from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    detailed_type = fields.Selection(selection_add=[
        ('product', 'Storable Product'),
        ('transport', 'Transport'),
    ], tracking=True, ondelete={'product': 'set consu', 'transport': 'set consu'}, default='product')
    type = fields.Selection(selection_add=[
        ('product', 'Storable Product'),
        ('transport', 'Transport'),
    ], ondelete={'product': 'set consu', 'transport': 'set consu'}, default='product')

    box_weight = fields.Float(string='Box Weight [kg]')
