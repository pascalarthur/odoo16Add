from odoo import models, api, fields, http


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    selected_for_action = fields.Boolean(string='Selected for Action')

    @api.model
    def sell_selected_products(self):
        selected_quants = self.search([('selected_for_action', '=', True)])

        if not selected_quants:
            return False  # No selected products

        # Create a new sales order
        SaleOrder = self.env['sale.order']
        sale_order = SaleOrder.create({
            'partner_id': self.env.user.partner_id.id,  # Example: setting the current user's partner
            'location_id': selected_quants[0].location_id.id,

            # Add other necessary fields for the sale.order
        })

        # Add products to the sales order
        for quant in selected_quants:
            sale_order.write({
                'order_line': [(0, 0, {
                    'product_id': quant.product_id.id,
                    'product_uom_qty': quant.quantity,
                    'product_uom': quant.product_id.uom_id.id,
                    'price_unit': quant.product_id.lst_price,
                    # Add other necessary fields for the sale.order.line
                })]
            })

        selected_quants.write({'selected_for_action': False})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': sale_order.id,
            'target': 'new',
            'context': {
                'default_create_date': fields.Datetime.now(),  # Store creation time
            },
        }

class StockQuantController(http.Controller):
    @http.route('/fish_market/sell_selected_products', type="json", auth="user")
    def sell_selected_products(self):
        stock_quant = http.request.env['stock.quant']

        return stock_quant.sell_selected_products()
