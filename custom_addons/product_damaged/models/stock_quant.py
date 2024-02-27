from odoo import models, fields, api, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    quantity_damaged = fields.Float('Damaged Quantity', default=0)
    _use_adjusted_name_on_stock_move_line = fields.Boolean('Adjustment Name')

    @api.onchange('quantity_damaged')
    def _onchange_quantity_damaged(self):
        for quant in self:
            if quant.product_id and quant.quantity_damaged > 0:
                # Raises error if the product is already marked as damaged and set the quantity_damaged to 0
                try:
                    quant.product_id.compute_product_as_damaged()
                except Exception as e:
                    quant.action_clear_inventory_quantity()
                    return {
                        'warning': {
                            'title': _('Warning'),
                            'message': e.args[0],
                        }
                    }

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

    def _get_inventory_move_values(self, *args, **kwargs):
        res = super(StockQuant, self)._get_inventory_move_values(*args, **kwargs)
        # Change reason for inventory adjustment
        if self.quantity_damaged > 0 or self._use_adjusted_name_on_stock_move_line:
            res['name'] = _('Adjustment for Damaged Product')
            for line in res['move_line_ids']:
                line[-1]['is_product_damage_stock_move_line'] = True
        return res

    def action_apply_inventory(self):
        for quant in self:
            if quant.quantity_damaged > 0:
                # Adjust damaged product -> Create Damaged product
                damaged_product_id = quant.product_id.compute_product_as_damaged()
                damaged_quant_id = self.browse_create(quant.location_id, damaged_product_id)
                if damaged_quant_id.inventory_quantity_set:
                    damaged_quant_id.inventory_quantity += quant.quantity_damaged
                else:
                    damaged_quant_id.inventory_quantity = damaged_quant_id.quantity + quant.quantity_damaged

                damaged_quant_id._use_adjusted_name_on_stock_move_line = True
                damaged_quant_id.action_apply_inventory()
                damaged_quant_id._use_adjusted_name_on_stock_move_line = False

        super(StockQuant, self).action_apply_inventory()

        for quant in self:
            quant.action_clear_inventory_quantity()

    def action_clear_inventory_quantity(self):
        self.quantity_damaged = 0
        super(StockQuant, self).action_clear_inventory_quantity()

    @api.model
    def _get_inventory_fields_create(self):
        """ Returns a list of fields user can edit when he want to create a quant in `inventory_mode`.
        """
        return ['product_id', 'owner_id', 'quantity_damaged'] + self._get_inventory_fields_write()
