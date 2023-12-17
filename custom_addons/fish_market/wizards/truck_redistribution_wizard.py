from odoo import models, fields, api


class TruckRedistributionWizardLine(models.TransientModel):
    _name = 'truck.redistribution.wizard.line'
    _description = 'Truck Redistribution Wizard Line'

    wizard_id = fields.Many2one('redistribution.wizard', string='Wizard', readonly=True)
    meta_sale_order_id = fields.Many2one(related='wizard_id.meta_sale_order_id')
    truck_id = fields.Many2one(related='wizard_id.truck_id')

    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Integer(string='Quantity')

    target_truck_id = fields.Many2one(
        'truck.detail',
        string='Target Truck',
    )



class LocationRedistributionWizardLine(models.TransientModel):
    _name = 'location.redistribution.wizard.line'
    _description = 'Location Redistribution Wizard Line'

    wizard_id = fields.Many2one('redistribution.wizard', string='Wizard', readonly=True)
    meta_sale_order_id = fields.Many2one(related='wizard_id.meta_sale_order_id')

    location_dest_id = fields.Many2one('stock.location', string='Target Location')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Integer(string='Quantity')


class RedistributionWizard(models.TransientModel):
    _name = 'redistribution.wizard'
    _description = 'Redistribution Wizard'

    move_to_stock = fields.Boolean(default=False)
    redistribute = fields.Boolean(default=False)

    truck_id = fields.Many2one('truck.detail', string='Truck', readonly=True)
    meta_sale_order_id = fields.Many2one('meta.sale.order', string="Meta Sale Order", readonly=True)

    truck_redistribution_lines = fields.One2many(
        'truck.redistribution.wizard.line', 'wizard_id', string='Redistribution Trucks'
    )

    location_redistribution_lines = fields.One2many(
        'location.redistribution.wizard.line', 'wizard_id', string='Redistribution Locations'
    )

    def confirm_action(self):
        self.ensure_one()
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']

        if self.redistribute:
            for truck_line in self.truck_redistribution_lines:
                # Decrease quantity in source truck
                source_load_line = self.truck_id.load_line_ids.filtered(lambda l: l.product_id == truck_line.product_id)
                if source_load_line:
                    source_load_line.quantity -= truck_line.quantity

                # Increase quantity in target truck
                target_load_line = truck_line.target_truck_id.load_line_ids.filtered(lambda l: l.product_id == truck_line.product_id)
                if target_load_line:
                    target_load_line.quantity += truck_line.quantity
                else:
                    # Create a new truck.detail.line if it doesn't exist
                    self.env['truck.detail.line'].create({
                        'truck_detail_id': truck_line.target_truck_id.id,
                        'product_id': truck_line.product_id.id,
                        'quantity': truck_line.quantity,
                    })

        if self.move_to_stock:
            for location_line in self.location_redistribution_lines:
                for load_line in self.truck_id.load_line_ids:
                    if load_line.product_id == location_line.product_id:
                        load_line.quantity -= location_line.quantity
                        break

                picking = StockPicking.create({
                    'location_id': load_line.location_id.id,
                    'location_dest_id': location_line.location_dest_id.id,
                    'picking_type_id': self._get_picking_type().id,
                    'origin': self.meta_sale_order_id.name,
                })

                # Create a stock move for each product
                StockMove.create({
                    'name': location_line.product_id.name,
                    'product_id': location_line.product_id.id,
                    'product_uom_qty': location_line.quantity,
                    'product_uom': location_line.product_id.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': load_line.location_id.id,
                    'location_dest_id': location_line.location_dest_id.id,
                })

    def _get_picking_type(self):
        # Return the picking type (e.g., internal transfer)
        # This is an example, adapt it to your specific needs
        return self.env.ref('stock.picking_type_internal')