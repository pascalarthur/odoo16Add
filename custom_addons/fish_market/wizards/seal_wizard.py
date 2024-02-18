from odoo import models, fields, api


class RedistributionWizard(models.TransientModel):
    _name = 'seal.wizard'
    _description = 'Seal Wizard'

    truck_route_id = fields.Many2one('truck.route', string='Truck', readonly=True)
    seal_number = fields.Char(string='Seal Number')

    def confirm_action(self):
        self.ensure_one()
        self.truck_route_id.seal_number = self.seal_number
