import pytz
from datetime import datetime
from odoo import fields, models


class TestModel(models.Model):
    _name = 'test_model'
    _description = 'Collect fish prices here to make better purchase decisions.'

    namibia_tz = pytz.timezone('Africa/Windhoek')
    name = fields.Char(default=datetime.now(namibia_tz).strftime("%d/%m/%Y %H:%M:%S"), readonly=True)

    Date = fields.Date(default=fields.Date.context_today)
    Vendor = fields.Many2one('res.partner', string="Vendor") #  fields.Many2one('vendor.model', string="Vendor", required=True)
    Product = fields.Many2one('product.product', string='Product')
    information = fields.Char()
    Size = fields.Float()
    Quantity = fields.Float()

    def _default_currency(self):
        return self.env['res.currency'].search([('name', '=', 'N$')], limit=1).id

    Price = fields.Monetary(currency_field='Currency', default=0.0)
    Currency = fields.Many2one('res.currency', string='Currency', default=_default_currency)

    def action_buy(self):
        self.ensure_one()
        purchase_order_obj = self.env['purchase.order']
        purchase_order_line_obj = self.env['purchase.order.line']

        # Create a purchase order
        order_vals = {
            'partner_id': self.Vendor.id,  # Assuming you have a vendor_id field
            'date_order': fields.Date.context_today(self),
            # Other necessary fields
        }
        order = purchase_order_obj.create(order_vals)

        # Add a line to the purchase order
        line_vals = {
            'order_id': order.id,
            'product_id': self.Product.id,  # Assuming you have a product_id field
            'name': 'Fish',
            'product_qty': self.Quantity,  # Assuming you have a quantity field
            'product_uom': self.Product.uom_id.id,
            'price_unit': self.Price,
            'date_planned': fields.Date.context_today(self),
            'currency_id': self.Currency.id,
            # Other necessary fields
        }
        purchase_order_line_obj.create(line_vals)

        # Redirect to the newly created purchase order
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'res_id': order.id,
            'view_mode': 'form',
        }
