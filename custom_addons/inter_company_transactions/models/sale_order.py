from odoo import models, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            # Check if inter-company transactions are enabled
            if order.company_id.enable_inter_company_transactions:
                # Logic to determine the target company
                target_company = self.env['res.company'].search([...])

                # Create a corresponding Purchase Order
                purchase_order_vals = {
                    'partner_id': order.partner_id.id,
                    'company_id': target_company.id,
                    # Add other necessary fields and logic to mirror the sales order
                }
                self.env['purchase.order'].create(purchase_order_vals)

        return res
