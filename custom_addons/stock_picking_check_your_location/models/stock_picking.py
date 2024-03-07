from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate_check_location_wizard(self):
        return {
            'name': 'Check Location',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.check.location.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
            },
        }
