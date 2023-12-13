from odoo import models, fields, api, _


TRANSPORT_ORDER_STATE =[
    ('draft', 'RFT'),
    ('sent', 'RFT Sent'),
    ('received', 'Offer Received'),
]

class TransportOrder(models.Model):
    _name = 'transport.order'
    _description = 'Transport Order'

    name = fields.Char(
        string="Transport Reference",
        required=True, copy=False, readonly=False,
        index='trigram',
        default=lambda self: self._default_name())

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

    supplier_id = fields.Many2one('res.partner')

    state = fields.Selection(
        selection=TRANSPORT_ORDER_STATE,
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='sent')

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