from odoo import models, fields, api, exceptions


class RedistributionWizardLineBase(models.TransientModel):
    _name = 'redistribution.wizard.line.base'
    _description = 'Redistribution Wizard Line Base'

    wizard_id = fields.Many2one('redistribution.wizard', string='Wizard', readonly=True)
    meta_sale_order_id = fields.Many2one(related='wizard_id.meta_sale_order_id')
    truck_route_id = fields.Many2one(related='wizard_id.truck_route_id')
    load_line_ids = fields.One2many(related='wizard_id.truck_route_id.load_line_ids')
    product_ids_from_load_lines = fields.Many2many('product.product', compute='_compute_product_ids_from_load_lines')

    @api.depends('load_line_ids')
    def _compute_product_ids_from_load_lines(self):
        for record in self:
            product_ids = record.load_line_ids.mapped('product_id.id')
            record.product_ids_from_load_lines = [(6, 0, product_ids)]

    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Integer(string='Quantity')


class LocationRedistributionWizardLine(RedistributionWizardLineBase):
    _name = 'location.redistribution.wizard.line'
    _description = 'Location Redistribution Wizard Line'

    location_dest_id = fields.Many2one('stock.location', string='Target Location')


class TruckRedistributionWizardLine(RedistributionWizardLineBase):
    _name = 'truck.redistribution.wizard.line'
    _description = 'Truck Redistribution Wizard Line'

    target_truck_route_id = fields.Many2one('truck.route', string='Target Truck')


class RedistributionWizard(models.TransientModel):
    _name = 'redistribution.wizard'
    _description = 'Redistribution Wizard'

    move_to_stock = fields.Boolean(default=False)
    redistribute = fields.Boolean(default=False)

    truck_route_id = fields.Many2one('truck.route', string='Truck Route', readonly=True)
    meta_sale_order_id = fields.Many2one('meta.sale.order', string="Meta Sale Order", readonly=True)
    load_line_ids = fields.One2many(related='truck_route_id.load_line_ids')

    truck_redistribution_lines = fields.One2many('truck.redistribution.wizard.line', 'wizard_id',
                                                 string='Redistribution Trucks')

    location_redistribution_lines = fields.One2many('location.redistribution.wizard.line', 'wizard_id',
                                                    string='Redistribution Locations')

    def _adjust_receipt_picking(self, redistribution_line):
        # Adjust receipt note
        picking_receipt = self.truck_route_id.picking_receipt_ids[0]
        move_line = picking_receipt.move_ids.filtered(lambda m: m.product_id == redistribution_line.product_id)
        if move_line:
            move_line.product_uom_qty -= redistribution_line.quantity

    def _redistribute_to_other_truck(self):
        for truck_line in self.truck_redistribution_lines:
            # Decrease quantity in source truck
            source_load_line = self.truck_route_id.load_line_ids.filtered(
                lambda l: l.product_id == truck_line.product_id)
            if source_load_line:
                source_load_line.quantity -= truck_line.quantity
                if source_load_line.quantity == 0:
                    source_load_line.unlink()

            # Increase quantity in target truck
            target_load_line = truck_line.target_truck_route_id.load_line_ids.filtered(
                lambda l: l.product_id == truck_line.product_id)
            if target_load_line:
                target_load_line.quantity += truck_line.quantity
            else:
                # Create a new truck.route.line if it doesn't exist
                self.env['truck.route.line'].create({
                    'truck_route_id': truck_line.target_truck_route_id.id,
                    'product_id': truck_line.product_id.id,
                    'quantity': truck_line.quantity,
                })

            # Increase the receipt on the target truck
            picking_receipt = truck_line.target_truck_route_id.picking_receipt_ids[0]
            move_line = picking_receipt.move_ids.filtered(lambda m: m.product_id == truck_line.product_id)
            if move_line:
                move_line.product_uom_qty += truck_line.quantity

            # Decrease the receipt on the source truck
            self._adjust_receipt_picking(truck_line)

    def _move_to_stock(self):
        for location_line in self.location_redistribution_lines:
            load_lines_to_unlink = []
            for load_line in self.truck_route_id.load_line_ids:
                if load_line.product_id == location_line.product_id:
                    load_line.quantity -= location_line.quantity
                    if load_line.quantity == 0:
                        load_lines_to_unlink.append(load_line)
                    break

            picking = self.env['stock.picking'].create({
                'location_id': load_line.location_id.id,
                'location_dest_id': location_line.location_dest_id.id,
                'picking_type_id': self._get_picking_type().id,
                'origin': self.meta_sale_order_id.name,
            })

            # Create a stock move for each product
            self.env['stock.move'].create({
                'name': location_line.product_id.name,
                'product_id': location_line.product_id.id,
                'product_uom_qty': location_line.quantity,
                'product_uom': location_line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': load_line.location_id.id,
                'location_dest_id': location_line.location_dest_id.id,
            })
            for load_line in load_lines_to_unlink:
                load_line.unlink()

            self._adjust_receipt_picking(location_line)

    def confirm_action(self):
        self.ensure_one()

        for load_line in self.truck_route_id.load_line_ids:
            loaded_quantity = sum(
                self.truck_route_id.load_line_ids.filtered(lambda l: l.product_id == load_line.product_id).mapped(
                    'quantity'))
            desired_unload_quantity = sum(
                self.location_redistribution_lines.filtered(lambda l: l.product_id == load_line.product_id).mapped(
                    'quantity'))
            desired_unload_quantity += sum(
                self.truck_redistribution_lines.filtered(lambda l: l.product_id == load_line.product_id).mapped(
                    'quantity'))

            if desired_unload_quantity > loaded_quantity:
                raise exceptions.UserError(
                    f"The quantity of product {load_line.product_id.name} to be unloaded is greater than the quantity loaded"
                )

        if self.redistribute:
            self._redistribute_to_other_truck()

        if self.move_to_stock:
            self._move_to_stock()

    def _get_picking_type(self):
        # Return the picking type (e.g., internal transfer)
        # This is an example, adapt it to your specific needs
        return self.env.ref('stock.picking_type_internal')
