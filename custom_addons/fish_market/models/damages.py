from odoo import models, fields, api, _
from odoo import exceptions

from collections import defaultdict

from ..utils.model_utils import default_name


class Damage(models.Model):
    _name = 'inventory.damage'
    _description = 'Records Damages to boxes'

    damage_id = fields.Many2one('inventory.damage.operation', string='Damage Operation', ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Location', required=True)
    source_product_id = fields.Many2one('product.product', string='Product', required=True, domain=lambda self: self._available_products())
    damaged_product_id = fields.Many2one('product.product', string='Damaged Product', compute='_compute_product_as_damaged', required=True)
    quantity = fields.Float('Quantity', required=True)
    stock_quant_id = fields.Many2one('stock.quant', string='Stock Quant', compute='_compute_stock_quant_id', store=True)

    @api.depends('location_id')
    def _available_products(self):
        domain = [('quantity', '>', 0)]
        return [('id', 'in', self.env['stock.quant'].search(domain).mapped('product_id.id'))]

    @api.depends('location_id', 'source_product_id')
    def _compute_stock_quant_id(self):
        for record in self:
            if record.location_id.id != False and record.source_product_id.id != False:
                record.stock_quant_id = self.env['stock.quant'].search([('location_id', '=', record.location_id.id),
                                                                        ('product_id', '=', record.source_product_id.id)])
                if record.stock_quant_id.id == False:
                    raise exceptions.UserError(_(f'No stock found for {record.source_product_id.name} at {record.location_id.name}'))

    @api.depends('source_product_id')
    def _compute_product_as_damaged(self):
        for record in self:
            record.damaged_product_id = False
            if record.source_product_id.id != False:
                attribute_values = self.env['product.template.attribute.value'].search([('product_tmpl_id', '=', record.source_product_id.product_tmpl_id.id)])
                attribute_values_map = {}
                for attr_val in attribute_values:
                    if attr_val.attribute_id.name == "Quality":
                        attribute_values_map[attr_val.name] = attr_val.id

                if attribute_values_map == {}:
                    raise exceptions.UserError(_(f"'Quality'-attribute on product {record.source_product_id.product_tmpl_id.name} not found.\
                                                 Go to product template 'Attributes & Variants' and add attribute 'Quality'"))

                attributes = map(int, record.source_product_id.combination_indices.split(','))
                attributes_damaged = set([x if x != attribute_values_map['OK'] else attribute_values_map['Damaged'] for x in attributes])

                for product in self.env['product.product'].search([('product_tmpl_id', '=', record.source_product_id.product_tmpl_id.id)]):
                    if set(map(int, product.combination_indices.split(','))) == attributes_damaged:
                        record.damaged_product_id = product

                if record.damaged_product_id.id == False:
                    raise exceptions.UserError(_(f'Damaged Product not found for {record.source_product_id.name}'))


class DamageOperation(models.Model):
    _name = 'inventory.damage.operation'
    _description = 'Records Damages to boxes'

    name = fields.Char(
        string="Reference",
        required=True, copy=False, readonly=False,
        index='trigram',
        default=lambda self: default_name(self, prefix='DAM/'))

    state = fields.Selection(
        selection=[('draft', 'Draft'),
                   ('confirmed', 'Confirmed')],
        string="Status",
        readonly=True, copy=False, index=True,
        default='draft')

    damage_line_ids = fields.One2many('inventory.damage', 'damage_id', string='Damage Lines')

    def action_confirm(self):
        self.state = 'confirmed'
        for line in self.damage_line_ids:
            if line.stock_quant_id.quantity < line.quantity:
                raise exceptions.UserError(_(f'Not enough stock for {line.source_product_id.name} at {line.location_id.name}'))

            line.stock_quant_id.write({'quantity': line.stock_quant_id.quantity - line.quantity})

            existing_quant_id = self.env['stock.quant'].search([('location_id', '=', line.location_id.id),
                                                            ('product_id', '=', line.damaged_product_id.id)])
            if existing_quant_id.id == False:
                self.env['stock.quant'].create({'location_id': line.location_id.id,
                                                'product_id': line.damaged_product_id.id,
                                                'quantity': line.quantity})
            else:
                existing_quant_id.write({'quantity': existing_quant_id.quantity + line.quantity})

