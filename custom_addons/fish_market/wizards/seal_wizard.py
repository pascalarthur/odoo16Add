from odoo import models, fields, api


class RedistributionWizard(models.TransientModel):
    _name = 'seal.wizard'
    _description = 'Seal Wizard'

    truck_id = fields.Many2one('truck.detail', string='Truck', readonly=True)
    seal_number = fields.Char(string='Seal Number')

    def confirm_action(self):
        self.ensure_one()
        self.truck_id.seal_number = self.seal_number
