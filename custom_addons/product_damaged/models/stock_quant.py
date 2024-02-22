from odoo import models, fields, api, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    quantity_damaged = fields.Float('Damaged Quantity', default=0)

    def write(self, vals):
        if 'quantity_damaged' in vals:
            for quant in self:
                # Adjust OK product -> Reduce Counted Quantity
                if vals['quantity_damaged'] != quant.quantity_damaged:
                    if quant.inventory_quantity_set:
                        quant.inventory_quantity += quant.quantity_damaged - vals['quantity_damaged']
                    else:
                        quant.inventory_quantity = quant.quantity - vals['quantity_damaged']
        return super(StockQuant, self).write(vals)

    @api.model
    def browse_create(self, location_id, product_id):
        quant = self.search([('location_id', '=', location_id.id), ('product_id', '=', product_id.id)], limit=1)
        if quant.id == False:
            quant = self.create({'location_id': location_id.id, 'product_id': product_id.id, 'quantity': 0})
        return quant

    def action_apply_inventory(self):
        for quant in self:
            if quant.quantity_damaged > 0:
                # Adjust damaged product -> Create Damaged product
                damaged_product_id = quant.product_id.compute_product_as_damaged()
                damaged_quant_id = self.browse_create(quant.location_id, damaged_product_id)
                damaged_quant_id.quantity += quant.quantity_damaged

        super(StockQuant, self).action_apply_inventory()

        for quant in self:
            quant.quantity_damaged = 0

    def action_clear_inventory_quantity(self):
        self.quantity_damaged = 0
        super(StockQuant, self).action_clear_inventory_quantity()
