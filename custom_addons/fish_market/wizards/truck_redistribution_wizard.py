from odoo import models, fields, api


class TruckRedistributionWizardLine(models.TransientModel):
    _name = 'truck_to_truck.redistribution.wizard.line'
    _description = 'Truck Redistribution Wizard Line'

    wizard_id = fields.Many2one('truck.redistribution.wizard', string='Wizard', readonly=True)
    meta_sale_order_id = fields.Many2one(related='wizard_id.meta_sale_order_id')

    target_truck_id = fields.Many2one('truck.detail', string='Target Truck') #, domain="[('meta_sale_order_id', '=', meta_sale_order_id)]")
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Integer(string='Quantity')


class LocationRedistributionWizardLine(models.TransientModel):
    _name = 'location.redistribution.wizard.line'
    _description = 'Location Redistribution Wizard Line'

    wizard_id = fields.Many2one('truck.redistribution.wizard', string='Wizard', readonly=True)
    meta_sale_order_id = fields.Many2one(related='wizard_id.meta_sale_order_id')

    target_location_id = fields.Many2one('stock.quant', string='Target Location')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Integer(string='Quantity')


class RedistributionWizard(models.TransientModel):
    _name = 'truck.redistribution.wizard'
    _description = 'Redistribution Wizard'

    action_selection = fields.Selection([
        ('zambia_stock', 'Move to WvB - Zambia Stock'),
        ('redistribute', 'Redistribute to another truck'),
    ], string='Action', required=True, default='zambia_stock')

    truck_id = fields.Many2one('truck.detail', string='Truck', readonly=True)
    meta_sale_order_id = fields.Many2one('meta.sale.order', string="Meta Sale Order", readonly=True)

    truck_redistribution_lines = fields.One2many(
        'truck_to_truck.redistribution.wizard.line', 'wizard_id', string='Redistribution Lines'
    )

    location_redistribution_lines = fields.One2many(
        'location.redistribution.wizard.line', 'wizard_id', string='Redistribution Lines'
    )

    def confirm_action(self):
        self.ensure_one()
        if self.action_selection == 'zambia_stock':
            # Logic for moving to Zambia Stock
            pass
        elif self.action_selection == 'redistribute':
            print(self.truck_redistribution_lines)
            print(self.meta_sale_order_id)
            pass
