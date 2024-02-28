from odoo import fields, models


class InheritedModel(models.Model):
    _inherit = "purchase.order"

    def _default_currency(self):
        return self.env['res.currency'].search([('name', '=', 'N$')], limit=1).id

    currency_id = fields.Many2one('res.currency', string='Currency', default=_default_currency)

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order')
    truck_route_id = fields.Many2one('truck.route', string='Truck Detail')
