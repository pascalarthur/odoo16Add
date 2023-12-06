import pytz
from datetime import datetime
from odoo import fields, models


class PriceCollectionModel(models.Model):
    _name = 'test_model'
    _description = 'Collect fish prices here to make better purchase decisions.'

    namibia_tz = pytz.timezone('Africa/Windhoek')
    reference = fields.Char(default=datetime.now(namibia_tz).strftime("%d/%m/%Y %H:%M:%S"), string='Reference', readonly=True)

    date = fields.Date(default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string='Supplier') # , default=lambda self: self.env.user.partner_id
    product_id = fields.Many2one('product.product', string='Product')
    size = fields.Float(string='Size')
    quantity = fields.Float(string='Quantity')

    def _default_currency(self):
        return self.env['res.currency'].search([('name', '=', 'N$')], limit=1).id

    price = fields.Monetary(currency_field='currency_id', string='Price', default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency', default=_default_currency)

    def action_buy(self):
        if not self:
            return

        purchase_order_obj = self.env['purchase.order']
        purchase_order_line_obj = self.env['purchase.order.line']

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
            order = purchase_order_obj.create(order_vals)
            orders.append(order.id)

            # Add a line to the purchase order for each record
            for record in records:
                line_vals = {
                    'order_id': order.id,
                    'product_id': record.product_id.id,
                    'name': 'Fish',
                    'product_qty': record.quantity,
                    'product_uom': record.product_id.uom_id.id,
                    'price_unit': record.price,
                    'date_planned': fields.Date.context_today(record),
                    'currency_id': record.currency_id.id,
                    # Other necessary fields
                }
                purchase_order_line_obj.create(line_vals)

        quotation_management = self.env['quotation.management'].create({
            'name': 'Your Reference Name',
            'purchase_order_ids': [(6, 0, orders)],  # 'orders' is a list of purchase order IDs
        })

        # Redirect to the new form view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation Management',
            'res_model': 'quotation.management',
            'res_id': quotation_management.id,
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

