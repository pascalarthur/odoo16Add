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
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    unit_price = fields.Float('Unit Price', default=0.0)
    location_id = fields.Many2one('stock.location', string='Origin Location')
    quantity = fields.Float(string='Quantity', default=1.0)



class TruckDetail(models.Model):
    _name = 'truck.detail'
    _description = 'Truck Detail'

    name = fields.Char(
        string="Truck Ref",
        required=True, copy=False, readonly=False,
        index='trigram',
        default=lambda self: default_name(self, prefix='TR'))

    state = fields.Selection(
        selection=TRUCK_STATES,
        string="Status",
        readonly=True, copy=False, index=True,
        default='offer')

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order', ondelete='cascade')
    partner_id = fields.Many2one('res.partner')
    transport_order_id  = fields.Many2one('transport.order', string='Transport Order', ondelete='cascade')
    is_backload = fields.Boolean(string='Is Backload', default=False)

    truck_number = fields.Char(string='Trailer Number')
    horse_number = fields.Char(string='Horse Number')
    container_number = fields.Char(string='Container Number')
    driver_name = fields.Char(string='Driver Name')
    telephone_number = fields.Char(string='Telephone Number')

    seal_number = fields.Char(string='Seal Number')

    price = fields.Float(string='Price')
    max_load = fields.Float(string='Max. Load [kg]')
    price_per_kg = fields.Float(string='Price per Kg', compute='_compute_price_per_kg', digits=(4, 4))
    truck_utilization = fields.Float(string='Truck Utilization (%)', compute='_compute_truck_utilization', store=True)

    load_line_ids = fields.One2many('truck.detail.line', 'truck_detail_id', string='Load Lines')

    @api.depends('load_line_ids.quantity', 'max_load')
    def _compute_truck_utilization(self):
        for record in self:
            total_allocated_quantity = sum(line.quantity * line.product_id.weight for line in record.load_line_ids)
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

    def allocate_product(self, product, unit_price, location_id, quantity):
        self.ensure_one()
        self.state = 'confirmed'
        self.env['truck.detail.line'].create({
            'truck_detail_id': self.id,
            'product_id': product.id,
            'unit_price': unit_price,
            'location_id': location_id.id,
            'quantity': quantity,
        })

    def action_handle_overload(self):
        truck_redistribution = self.env['redistribution.wizard'].create({
                'truck_id': self.id,
                'meta_sale_order_id': self.meta_sale_order_id.id,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'redistribution.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': truck_redistribution.id,
            'target': 'new',
            'context': {
            },
        }


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
    route_start_state_id = fields.Many2one('res.country.state')
    route_start_country_id = fields.Many2one('res.country')

    route_end_street = fields.Char()
    route_end_street2 = fields.Char()
    route_end_city = fields.Char()
    route_end_zip = fields.Char()
    route_end_state_id = fields.Many2one('res.country.state')
    route_end_country_id = fields.Many2one('res.country')

    truck_ids = fields.One2many('truck.detail', 'transport_order_id', string='Truck Details')

    container_demand = fields.Integer(string='Container Demand')
    container_offer = fields.Integer(string='Container Offer', compute='_compute_container_offer')
    additional_details = fields.Text(string='Additional Details')

    product_template_id = fields.Many2one('product.template', string='Product Template')

    partner_id = fields.Many2one('res.partner')

    state = fields.Selection(
        selection=TRANSPORT_ORDER_STATES,
        string="Status",
        readonly=True, copy=False, index=True,
        default='sent')

    price = fields.Float(string='Price')


    def confirm_price(self):
        self.state = 'received'

    @api.depends('truck_ids')
    def _compute_container_offer(self):
        for record in self:
            record.container_offer = len(record.truck_ids)
