from odoo import fields, models


class PriceCollectionItem(models.Model):
    _inherit = 'product.pricelist.item'
    _description = 'Collect fish prices here to make better purchase decisions.'

    partner_id = fields.Many2one('res.partner', string='Supplier')
    truck_id = fields.Many2one('truck.detail', string='Truck')

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order')
    backload_id = fields.Many2one('product.pricelist.item', string='Backload')
    is_backload = fields.Boolean(string='Is Backload', compute='_is_backload')

    notes = fields.Text(string='Notes')

    backload_fixed_price = fields.Monetary(string='Backload Fixed Price', compute='_get_backload_fixed_price')

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
                Purchase_order_line_obj.create(line_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_ask_exporters(self):
        for record in self:
            export_partner_ids = self.env['res.partner'].search([('category_id.name', '=', 'Exporter')])

            return {
                'name': 'Select Pricelist',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'product.offer.wizard',
                'target': 'new',
                'context': {
                    'default_available_product_pricelist_item': self.ids,
                    'default_partner_ids': export_partner_ids.ids,
                    'default_pricelist_id': record.pricelist_id.id,
                    'default_email_body': f'Please fill in your price details by following the link below:',
                },
            }

    def _is_backload(self):
        attribute_values = self.env['product.template.attribute.value'].search([])
        for record in self:
            product_variants_map = {attr_val.id: attr_val.name for attr_val in attribute_values}
            for comb in record.product_id.mapped('combination_indices'):
                record.is_backload = any([product_variants_map[key] == 'Backload' for key in map(int, comb.split(','))])

    def _get_backload_fixed_price(self):
        for record in self:
            if not record.is_backload and record.backload_id:
                record.backload_fixed_price = record.backload_id.fixed_price
            else:
                record.backload_fixed_price = False