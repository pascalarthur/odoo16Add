from odoo import models, fields, api, _
from ..utils.model_utils import default_name


TRUCK_STATES =[
    ('offer', 'Offer'),
    ('confirmed', 'Confirmed'),
]


TRANSPORT_ORDER_STATES =[
    ('draft', 'RFT'),
    ('sent', 'RFT Sent'),
    ('received', 'Offer Received'),
]


class TruckLoadLine(models.Model):
    _name = 'truck.detail.line'
    _description = 'Truck Detail Line'

    truck_detail_id = fields.Many2one('truck.detail', string='Truck Detail', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    location_id = fields.Many2one('stock.location', string='Origin Location')
    quantity = fields.Float(string='Quantity', default=1.0)



class TruckDetail(models.Model):
    _name = 'truck.detail'
    _description = 'Truck Detail'

    state = fields.Selection(
        selection=TRUCK_STATES,
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='offer')

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order')
    transport_order_id  = fields.Many2one('transport.order', string='Transport Order')

    truck_number = fields.Char(string='Truck Number')
    horse_number = fields.Char(string='Horse Number')
    container_number = fields.Char(string='Container Number')
    driver_name = fields.Char(string='Driver Name')
    telephone_number = fields.Char(string='Telephone Number')

    seal_number = fields.Char(string='Seal Number')

    price = fields.Float(string='Price')
    max_load = fields.Float(string='Max. Load [kg]')
    price_per_kg = fields.Float(string='Price per Kg', compute='_compute_price_per_kg', digits=(4, 4))
    truck_utilization = fields.Float(string='Truck Utilization (%)', compute='_compute_truck_utilization')

    load_line_ids = fields.One2many('truck.detail.line', 'truck_detail_id', string='Load Lines')

    @api.depends('load_line_ids.quantity', 'max_load')
    def _compute_truck_utilization(self):
        for record in self:
            total_allocated_quantity = sum(line.quantity for line in record.load_line_ids)
            if record.max_load > 0:
                record.truck_utilization = (total_allocated_quantity / record.max_load) * 100
            else:
                record.truck_utilization = 0  # To handle cases where max_load is 0 or undefined

    @api.depends('price', 'max_load')
    def _compute_price_per_kg(self):
        for record in self:
            if record.max_load > 0.0:
                record.price_per_kg = record.price / record.max_load
            else:
                record.price_per_kg = 0.0

    def allocate_product(self, product, location_id, quantity):
        self.ensure_one()
        self.state = 'confirmed'
        self.env['truck.detail.line'].create({
            'truck_detail_id': self.id,
            'product_id': product.id,
            'location_id': location_id.id,
            'quantity': quantity,
        })



class TransportOrder(models.Model):
    _name = 'transport.order'
    _description = 'Transport Order'

    name = fields.Char(
        string="Transport Reference",
        required=True, copy=False, readonly=False,
        index='trigram',
        default=lambda self: default_name(self, prefix='T'))

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order')

    route_start_street = fields.Char()
    route_start_street2 = fields.Char()
    route_start_city = fields.Char()
    route_start_zip = fields.Char()
    route_start_state_id = fields.Many2one('res.country.state', string='State')
    route_start_country_id = fields.Many2one('res.country', string='Country')

    route_end_street = fields.Char()
    route_end_street2 = fields.Char()
    route_end_city = fields.Char()
    route_end_zip = fields.Char()
    route_end_state_id = fields.Many2one('res.country.state', string='State')
    route_end_country_id = fields.Many2one('res.country', string='Country')

    truck_ids = fields.One2many('truck.detail', 'transport_order_id', string='Truck Details')

    container_demand = fields.Integer(string='Container Demand')
    container_offer = fields.Integer(string='Container Offer', compute='_compute_container_offer')
    additional_details = fields.Text(string='Additional Details')

    partner_id = fields.Many2one('res.partner')

    state = fields.Selection(
        selection=TRANSPORT_ORDER_STATES,
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='sent')

    price = fields.Float(string='Price')


    def confirm_price(self):
        self.state = 'received'

    @api.depends('truck_ids')
    def _compute_container_offer(self):
        for record in self:
            record.container_offer = len(record.truck_ids)
