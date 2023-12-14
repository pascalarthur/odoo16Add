from odoo import models, fields, api, _


TRANSPORT_ORDER_STATE =[
    ('draft', 'RFT'),
    ('sent', 'RFT Sent'),
    ('received', 'Offer Received'),
]


class TruckDetail(models.Model):
    _name = 'truck.detail'
    _description = 'Truck Detail'

    transport_order_id  = fields.Many2one('transport.order', string='Transport Order')

    truck_number = fields.Char(string='Truck Number')
    horse_number = fields.Char(string='Horse Number')
    container_number = fields.Char(string='Container Number')
    driver_name = fields.Char(string='Driver Name')
    telephone_number = fields.Char(string='Telephone Number')

    price = fields.Float(string='Price')
    max_load = fields.Float(string='Max Load [kg]')


class TransportOrder(models.Model):
    _name = 'transport.order'
    _description = 'Transport Order'

    name = fields.Char(
        string="Transport Reference",
        required=True, copy=False, readonly=False,
        index='trigram',
        default=lambda self: self._default_name())

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

    container_count = fields.Integer(string='Container Count')
    additional_details = fields.Text(string='Additional Details')

    partner_id = fields.Many2one('res.partner')

    state = fields.Selection(
        selection=TRANSPORT_ORDER_STATE,
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='sent')

    truck_ids = fields.One2many('truck.detail', 'transport_order_id', string='Truck Details')

    price = fields.Float(string='Price')

    def confirm_price(self):
        self.state = 'received'

    @api.model
    def _default_name(self):
        # Retrieve the last number used
        last_order = self.search([], order='id desc', limit=1)
        if last_order and last_order.name.startswith('T'):
            last_number = int(last_order.name[1:])
            new_number = last_number + 1
        else:
            new_number = 1

        # Format the new number with leading zeros
        return 'T{:05d}'.format(new_number)