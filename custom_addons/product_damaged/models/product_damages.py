from odoo import models, fields, api, _
from odoo import exceptions


class Damage(models.Model):
    _name = 'inventory.damage'
    _description = 'Records Damages to boxes'

    damage_id = fields.Many2one('inventory.damage.operation', string='Damage Operation', ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Location', required=True)
    source_product_id = fields.Many2one('product.product', string='Product', required=True,
                                        domain=lambda self: self._available_products())
    damaged_product_id = fields.Many2one('product.product', string='Damaged Product',
                                         compute='_compute_product_as_damaged', required=True)
    quantity = fields.Float('Quantity', required=True)
    stock_quant_id = fields.Many2one('stock.quant', string='Stock Quant', compute='_compute_stock_quant_id', store=True)

    state = fields.Selection(selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('returned', 'Returned')], string="Status", readonly=True,
                             copy=False, index=True, default='draft')

    @api.depends('location_id')
    def _available_products(self):
        domain = [('quantity', '>', 0)]
        return [('id', 'in', self.env['stock.quant'].search(domain).mapped('product_id.id'))]

    @api.depends('location_id', 'source_product_id')
    def _compute_stock_quant_id(self):
        for record in self:
            if record.location_id.id != False and record.source_product_id.id != False:
                record.stock_quant_id = self.env['stock.quant'].search([('location_id', '=', record.location_id.id),
                                                                        ('product_id', '=', record.source_product_id.id)
                                                                        ])
                if record.stock_quant_id.id == False:
                    raise exceptions.UserError(
                        _(f'No stock found for {record.source_product_id.name} at {record.location_id.name}'))

    @api.depends('source_product_id')
    def _compute_product_as_damaged(self):
        for record in self:
            record.damaged_product_id = False
            if record.source_product_id.id != False:
                attribute_values = self.env['product.template.attribute.value'].search([
                    ('product_tmpl_id', '=', record.source_product_id.product_tmpl_id.id)
                ])
                attribute_values_map = {}
                for attr_val in attribute_values:
                    if attr_val.attribute_id.name == "Quality":
                        attribute_values_map[attr_val.name] = attr_val.id

                if attribute_values_map == {}:
                    raise exceptions.UserError(
                        _(f"'Quality'-attribute on product {record.source_product_id.product_tmpl_id.name} not found.\
                                                 Go to product template 'Attributes & Variants' and add attribute 'Quality'"
                          ))

                attributes = map(int, record.source_product_id.combination_indices.split(','))
                attributes_damaged = set(
                    [x if x != attribute_values_map['OK'] else attribute_values_map['Damaged'] for x in attributes])

                for product in self.env['product.product'].search([('product_tmpl_id', '=',
                                                                    record.source_product_id.product_tmpl_id.id)]):
                    if set(map(int, product.combination_indices.split(','))) == attributes_damaged:
                        record.damaged_product_id = product

                if record.damaged_product_id.id == False:
                    raise exceptions.UserError(_(f'Damaged Product not found for {record.source_product_id.name}'))

    @api.onchange('quantity')
    def _update_state(self):
        for record in self:
            if record.quantity == 0:
                record.state = 'returned'
            else:
                record.state = 'confirmed'


class DamageOperation(models.Model):
    _name = 'inventory.damage.operation'
    _description = 'Records Damages to boxes'

    name = fields.Char(string="Reference", copy=False, readonly=True)

    state = fields.Selection(selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('returned', 'Returned')],
                             string="Status", readonly=True, copy=False, index=True, default='draft')

    origin = fields.Char('Source Document', index='trigram', help="Reference of the document", readonly=True)
    damage_type = fields.Selection([('damaged', 'Damaged'), ('destroyed', 'Destroyed')], string='Damage Type',
                                   required=True, default='damaged')
    damage_tooltip = fields.Char('Damage Tooltip', compute='_compute_damage_tooltip', store=True)

    damage_line_ids = fields.One2many('inventory.damage', 'damage_id', string='Damage Lines')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('product.damages')
        return super(DamageOperation, self).create(vals)

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
                raise exceptions.UserError(
                    _(f'Not enough stock for {line.source_product_id.name} at {line.location_id.name}'))

            line.stock_quant_id.write({'quantity': line.stock_quant_id.quantity - line.quantity})

            if self.damage_type == 'damaged':
                existing_quant_id = self.env['stock.quant'].search([('location_id', '=', line.location_id.id),
                                                                    ('product_id', '=', line.damaged_product_id.id)])
                if existing_quant_id.id == False:
                    self.env['stock.quant'].create({
                        'location_id': line.location_id.id,
                        'product_id': line.damaged_product_id.id,
                        'quantity': line.quantity
                    })
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

    def adjust_for_return(self, stock_move_lines):
        for line in stock_move_lines:
            if line.quantity_damaged > 0:
                # 1. Update the inventory.damage line
                line.inventory_damage_id.write({'quantity': line.inventory_damage_id.quantity - line.quantity_damaged})

                # 2. Update the OK product quantity in stock.quant
                line.inventory_damage_id.stock_quant_id.write(
                    {'quantity': line.inventory_damage_id.stock_quant_id.quantity + line.quantity_damaged})

                # Check if damage_type is not 'destroyed' -> Then product does not exists
                if self.damage_type == 'damaged':
                    # 3. Update the Damaged product quantity in stock.quant
                    damaged_quant_id = self.env['stock.quant'].search([
                        ('location_id', '=', line.inventory_damage_id.location_id.id),
                        ('product_id', '=', line.inventory_damage_id.damaged_product_id.id)
                    ])
                    if damaged_quant_id.id == False:
                        self.env['stock.quant'].create({
                            'location_id': line.location_id.id,
                            'product_id': line.damaged_product_id.id,
                            'quantity': -line.quantity_damaged
                        })
                    else:
                        damaged_quant_id.write({'quantity': damaged_quant_id.quantity - line.quantity_damaged})

        # 4. Update the state of the inventory.damage
        if self.damage_line_ids:
            if all([line.quantity == 0 for line in self.damage_line_ids]):
                self.state = 'returned'


class StockPickingDamageLine(models.Model):
    _inherit = 'stock.move'

    quantity_damaged = fields.Float('Damaged Quantity')
    inventory_damage_id = fields.Many2one('inventory.damage', string='Inventory Damage')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    inventory_damage_id = fields.Many2one('inventory.damage.operation', string='Inventory Damage')

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if sum(self.move_ids_without_package.mapped('quantity_damaged')) > 0:
            if self.return_id and self.return_id.inventory_damage_id:
                # Return
                self.return_id.inventory_damage_id.adjust_for_return(self.move_ids_without_package)
            else:
                # Normal
                damage_operation = self.env['inventory.damage.operation'].create({"origin": self.name})
                for line in self.move_ids_without_package:
                    inventory_damage_id = self.env['inventory.damage'].create({
                        'damage_id': damage_operation.id,
                        'location_id': self.location_dest_id.id,
                        'source_product_id': line.product_id.id,
                        'quantity': line.quantity_damaged,
                    })
                    line.inventory_damage_id = inventory_damage_id.id
                damage_operation.action_confirm()
                self.inventory_damage_id = damage_operation.id
        return res
