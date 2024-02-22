from odoo import models, fields, api, exceptions, _


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    is_product_damage_stock_move_line = fields.Boolean('Is Damaged Operation', default=False)


class StockPickingDamageLine(models.Model):
    _inherit = 'stock.move'
    quantity_damaged = fields.Float('Damaged Quantity')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    inventory_damage_id = fields.Many2one('inventory.damage.operation', string='Inventory Damage')
    damaged_stock_picking_id = fields.Many2one('stock.picking', string='Damaged Stock Picking', readonly=True)
    damaged_stock_picking_ids = fields.One2many('stock.picking', 'damaged_stock_picking_id',
                                                string='Damaged Stock Pickings')
    damaged_stock_picking_ids_count = fields.Integer('Damaged Count',
                                                     compute='_compute_damaged_stock_picking_ids_count')
    is_damaged_picking = fields.Boolean('Is Damaged Picking', default=False)

    @api.depends('damaged_stock_picking_ids')
    def _compute_damaged_stock_picking_ids_count(self):
        for record in self:
            record.damaged_stock_picking_ids_count = len(record.damaged_stock_picking_ids)

    def button_validate(self):
        if self.picking_type_code == 'incoming':
            res = super(StockPicking, self).button_validate()

        if sum(self.move_ids_without_package.mapped('quantity_damaged')) > 0:
            stock_picking_return_id = self.create({
                'picking_type_id': self.picking_type_id.return_picking_type_id.id,
                'location_id': self.location_dest_id.id,
                'location_dest_id': self.location_id.id,
                'origin': self.name,
            })

            stock_picking_damaged_id = self.create({
                'picking_type_id': self.picking_type_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'origin': self.name,
                'is_damaged_picking': True,
            })

            for line in self.move_ids_without_package.filtered(lambda x: x.quantity_damaged > 0):
                stock_move_return_id = self.env['stock.move'].create({
                    'name': self.env['ir.sequence'].next_by_code('product.damages'),
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity_damaged,
                    'quantity': line.quantity_damaged,
                    'location_id': self.location_dest_id.id,
                    'location_dest_id': self.location_id.id,
                    'picking_id': stock_picking_return_id.id,
                    'origin': self.name,
                    'state': 'draft',
                })

                damaged_product_id = line.product_id.compute_product_as_damaged()
                stock_move_damaged_id = self.env['stock.move'].create({
                    'name': self.env['ir.sequence'].next_by_code('product.damages'),
                    'product_id': damaged_product_id.id,
                    'product_uom_qty': line.quantity_damaged,
                    'quantity': line.quantity_damaged,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'picking_id': stock_picking_damaged_id.id,
                    'origin': self.name,
                    'state': 'draft',
                })

            stock_move_return_id.move_line_ids.is_product_damage_stock_move_line = True
            stock_move_damaged_id.move_line_ids.is_product_damage_stock_move_line = True

            stock_picking_return_id.button_validate()
            stock_picking_damaged_id.button_validate()

            self.damaged_stock_picking_ids = [(4, stock_picking_return_id.id), (4, stock_picking_damaged_id.id)]

        if self.picking_type_code != 'incoming':
            res = super(StockPicking, self).button_validate()

        return res

    def action_damaged_stock_picking_ids(self):
        return {
            'name': _('Damaged Stock Pickings'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('id', 'in', self.damaged_stock_picking_ids.ids)],
        }
