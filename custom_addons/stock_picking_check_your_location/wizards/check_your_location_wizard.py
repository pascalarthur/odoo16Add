from odoo import api, models, fields


class StockPickingCheckLocationWizard(models.TransientModel):
    _name = 'stock.picking.check.location.wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking')
    location_id = fields.Many2one('stock.location', 'Source Location', related="picking_id.location_id", readonly=True)
    location_dest_id = fields.Many2one('stock.location', 'Destintation Location', related="picking_id.location_dest_id",
                                       readonly=True)

    def button_confirm(self):
        self.picking_id.location_id = self.location_id
        self.picking_id.location_dest_id = self.location_dest_id
        return self.picking_id.button_validate()
