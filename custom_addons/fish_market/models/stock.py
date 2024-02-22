from odoo import models, api, fields, http, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    selected_for_action = fields.Boolean(string='Selected for Action')

    @api.model
    def sell_selected_products(self):
        selected_quants = self.search([('selected_for_action', '=', True)])
        if not selected_quants:
            return False  # No selected products

        # Create a new meta sale order
        meta_sale_order = self.env['meta.sale.order'].create({})

        # Add selected products as order lines
        for quant in selected_quants:
            meta_sale_order.order_line_ids.create({
                'meta_sale_order_id': meta_sale_order.id,
                'product_id': quant.product_id.id,
                'location_id': quant.location_id.id,
                'quantity': quant.quantity,
                'unit_price': quant.product_id.list_price,
                'tax_ids': [(6, 0, quant.product_id.taxes_id.ids)],
            })

        selected_quants.write({'selected_for_action': False})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'meta.sale.order',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': meta_sale_order.id,
            'target': 'current',
            'context': {
                'default_create_date': fields.Datetime.now()
            },
        }


class StockQuantController(http.Controller):
    @http.route('/fish_market/sell_selected_products', type="json", auth="user")
    def sell_selected_products(self):
        stock_quant = http.request.env['stock.quant']

        return stock_quant.sell_selected_products()

    @http.route('/fish_market/process_damaged_products', type="json", auth="user")
    def process_damaged_products(self):
        inventory_damage_operation = http.request.env['inventory.damage.operation']

        return inventory_damage_operation.process_damaged_products()
