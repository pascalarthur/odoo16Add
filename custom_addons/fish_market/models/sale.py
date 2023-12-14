from odoo import api, models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    seal_number = fields.Char(string='Seal Number')
    transport_company_id = fields.Many2one('res.partner', string='Transport Company')
    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order')
    location_id = fields.Many2one('stock.location', string='Origin Location')

    @api.model
    def check_and_delete_order(self, order_id, creation_date):
        order = self.browse(order_id)
        # Check if the order was not modified (you might need to adjust this logic)
        if order.create_date == fields.Datetime.from_string(creation_date):
            order.unlink()  # Delete the order

    @api.model
    def create(self, vals):
        return super(SaleOrder, self).create(vals)
