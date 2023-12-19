from odoo import fields, models


class PriceCollectionItem(models.Model):
    _inherit = 'product.pricelist.item'
    _description = 'Collect fish prices here to make better purchase decisions.'

    partner_id = fields.Many2one('res.partner', string='Supplier')

    def action_buy(self):
        if not self:
            return

        Purchase_order_obj = self.env['purchase.order']
        Purchase_order_line_obj = self.env['purchase.order.line']

        # Group records by partner_id
        partner_groups = {}
        for record in self:
            partner_groups.setdefault(record.partner_id.id, []).append(record)

        orders = []

        # Create a purchase order for each partner group
        for partner_id, records in partner_groups.items():
            # Create one purchase order per partner
            order_vals = {
                'partner_id': partner_id,
                'date_order': fields.Date.context_today(self),
                # Other necessary fields
            }
            order = Purchase_order_obj.create(order_vals)
            orders.append(order.id)

            # Add a line to the purchase order for each record
            for record in records:
                line_vals = {
                    'order_id': order.id,
                    'product_id': record.product_id.id,
                    'name': 'Fish',
                    'product_qty': record.min_quantity,
                    'product_uom': record.product_id.uom_id.id,
                    'price_unit': record.fixed_price,
                    'date_planned': fields.Date.context_today(record),
                    'currency_id': record.currency_id.id,
                    # Other necessary fields
                }
                print(line_vals)
                Purchase_order_line_obj.create(line_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'target': 'current',
        }


    def action_save(self):
        return {
            'type': 'ir.actions.act_window_close'
        }
