import pytz
from datetime import datetime
from odoo import fields, models


class InheritedModel(models.Model):
    _inherit = "purchase.order"

    new_field = fields.Char(string="New Field")

    def _default_currency(self):
        return self.env['res.currency'].search([('name', '=', 'N$')], limit=1).id

    currency_id = fields.Many2one('res.currency', string='Currency', default=_default_currency)



class PriceCollectionModel(models.Model):
    _name = 'test_model'
    _description = 'Collect fish prices here to make better purchase decisions.'

    namibia_tz = pytz.timezone('Africa/Windhoek')
    reference = fields.Char(default=datetime.now(namibia_tz).strftime("%d/%m/%Y %H:%M:%S"), string='Reference', readonly=True)

    date = fields.Date(default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string="Vendor")
    product_id = fields.Many2one('product.product', string='Product')
    size = fields.Float(string='Size')
    quantity = fields.Float(string='Quantity')

    def _default_currency(self):
        return self.env['res.currency'].search([('name', '=', 'N$')], limit=1).id

    price = fields.Monetary(currency_field='currency_id', string='Price', default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency', default=_default_currency)

    def action_buy(self):
        self.ensure_one()
        purchase_order_obj = self.env['purchase.order']
        purchase_order_line_obj = self.env['purchase.order.line']

        # Create a purchase order
        order_vals = {
            'partner_id': self.partner_id.id,
            'date_order': fields.Date.context_today(self),
            # Other necessary fields
        }
        order = purchase_order_obj.create(order_vals)

        # Add a line to the purchase order
        line_vals = {
            'order_id': order.id,
            'product_id': self.product_id.id,
            'name': 'Fish',
            'product_qty': self.quantity,
            'product_uom': self.product_id.uom_id.id,
            'price_unit': self.price,
            'date_planned': fields.Date.context_today(self),
            'currency_id': self.currency_id.id,
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

    def action_save(self):
        return {
            'type': 'ir.actions.act_window_close'
        }


class WalvisBayPriceCollection(models.Model):
    _inherit = 'test_model'
    _name = 'walvis_bay_price_collection_model'


class ZambiaPriceCollection(models.Model):
    _inherit = 'test_model'
    _name = 'zambia_price_collection_model'
