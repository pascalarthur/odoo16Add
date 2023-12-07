from odoo import models, api, fields

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    selected_for_action = fields.Boolean(string='Selected for Action')

    def sell_selected_products(self):
        selected_products = self.search([('selected_for_action', '=', True)])
        for product in selected_products:
            # Your logic to handle the selling of the product
            # This could involve creating a sales order, updating stock, etc.
            pass
        # Optionally reset the selection
        selected_products.write({'selected_for_action': False})
