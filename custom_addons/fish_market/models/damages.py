from odoo import models, fields, api, _
from odoo import exceptions

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
        required=True, copy=False, readonly=True,
        index='trigram',
        default=lambda self: default_name(self, prefix='DAM/'))

    state = fields.Selection(
        selection=[('draft', 'Draft'),
                   ('confirmed', 'Confirmed')],
        string="Status",
        readonly=True, copy=False, index=True,
        default='draft')

    origin = fields.Char('Source Document', index='trigram', help="Reference of the document", readonly=True)
    damage_type = fields.Selection([('damaged', 'Damaged'), ('destroyed', 'Destroyed')], string='Damage Type', required=True, default='damaged')
    damage_tooltip = fields.Char('Damage Tooltip', compute='_compute_damage_tooltip', store=True)

    damage_line_ids = fields.One2many('inventory.damage', 'damage_id', string='Damage Lines')

    @api.depends('damage_type')
    def _compute_damage_tooltip(self):
        for record in self:
            if record.damage_type == 'damaged':
                record.damage_tooltip = 'The products will be converted from "OK" to "Damaged".'
            else:
                record.damage_tooltip = 'The products will be destroyed and removed from stock.'

    def action_confirm(self):
        for line in self.damage_line_ids:
            if line.stock_quant_id.quantity < line.quantity:
                raise exceptions.UserError(_(f'Not enough stock for {line.source_product_id.name} at {line.location_id.name}'))

            line.stock_quant_id.write({'quantity': line.stock_quant_id.quantity - line.quantity})

            if self.damage_type == 'damaged':
                existing_quant_id = self.env['stock.quant'].search([('location_id', '=', line.location_id.id),
                                                                ('product_id', '=', line.damaged_product_id.id)])
                if existing_quant_id.id == False:
                    self.env['stock.quant'].create({'location_id': line.location_id.id,
                                                    'product_id': line.damaged_product_id.id,
                                                    'quantity': line.quantity})
                else:
                    existing_quant_id.write({'quantity': existing_quant_id.quantity + line.quantity})
        self.state = 'confirmed'

    def process_damaged_products(self):
        selected_quants = self.env['stock.quant'].search([('selected_for_action', '=', True)])
        if not selected_quants:
            return False  # No selected products

        # Create a new meta sale order
        inventory_damage_operation_id = self.create({})

        # Add selected products as order lines
        for quant in selected_quants:
            inventory_damage_operation_id.damage_line_ids.create({
                'damage_id': inventory_damage_operation_id.id,
                'location_id': quant.location_id.id,
                'source_product_id': quant.product_id.id,
                'quantity': quant.quantity,
            })

        selected_quants.write({'selected_for_action': False})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'inventory.damage.operation',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': inventory_damage_operation_id.id,
            'target': 'current',
            'context': {},
        }


class StockPickingDamageLine(models.Model):
    _inherit = 'stock.move'

    quantity_damaged = fields.Float('Damaged Quantity')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if sum(self.move_ids_without_package.mapped('quantity_damaged')) > 0:
            damage_operation = self.env['inventory.damage.operation'].create({"origin": self.name})
            for line in self.move_ids_without_package:
                self.env['inventory.damage'].create({
                    'damage_id': damage_operation.id,
                    'location_id': self.location_dest_id.id,
                    'source_product_id': line.product_id.id,
                    'quantity': line.quantity_damaged,
                })
            damage_operation.action_confirm()
        return res
