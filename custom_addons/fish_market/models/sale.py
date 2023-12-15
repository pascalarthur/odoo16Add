from odoo import api, models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order')
    location_id = fields.Many2one('stock.location', string='Origin Location')
    truck_detail_id = fields.Many2one('truck.detail', string='Truck Detail')
    truck_number = fields.Char('Truck Number', related='truck_detail_id.truck_number',store=True)
    horse_number = fields.Char('Horse Number', related='truck_detail_id.horse_number',store=True)
    container_number = fields.Char('Container Number', related='truck_detail_id.container_number',store=True)
    seal_number = fields.Char('Seal Number', related='truck_detail_id.seal_number',store=True)
    driver_name = fields.Char('Driver Name', related='truck_detail_id.driver_name',store=True)
    telephone_number = fields.Char('Telephone Number', related='truck_detail_id.telephone_number',store=True)


    @api.model
    def check_and_delete_order(self, order_id, creation_date):
        order = self.browse(order_id)
        # Check if the order was not modified (you might need to adjust this logic)
        if order.create_date == fields.Datetime.from_string(creation_date):
            order.unlink()  # Delete the order
