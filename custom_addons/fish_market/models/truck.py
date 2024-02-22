from odoo import models, fields, api, _, exceptions
from ..utils.model_utils import default_name

TRUCK_STATES = [
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('loaded', 'Loaded'),
    ('done', 'Done'),
]


class TruckRouteLoadLine(models.Model):
    _name = "truck.route.line"
    _description = 'Truck Route Line'

    truck_route_id = fields.Many2one('truck.route', string='Truck Route', ondelete='cascade')
    available_product_ids = fields.One2many('product.product', related='truck_route_id.available_product_ids',
                                            store=False)
    location_id = fields.Many2one('stock.location', string='Origin Location')
    available_location_ids = fields.One2many('stock.location', related='truck_route_id.available_location_ids',
                                             store=False)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    unit_price = fields.Float('Unit Price', default=0.0)
    quantity = fields.Float(string='Quantity', default=1.0)
    tax_ids = fields.Many2many('account.tax', string='Taxes')


class TruckDetail(models.Model):
    _name = "truck.route"
    _description = 'Truck Route'

    name = fields.Char(string="Truck Ref", required=True, copy=False, readonly=False, index='trigram',
                       default=lambda self: default_name(self, prefix='TR'))

    state = fields.Selection(selection=TRUCK_STATES, string="Status", readonly=True, copy=False, index=True,
                             default='draft')

    truck_id = fields.Many2one('truck', string='Truck', ondelete='cascade')

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order', ondelete='cascade')
    is_backload = fields.Boolean(string='Is Backload', default=False)

    partner_id = fields.Many2one('res.partner', string="Transporter", related='truck_id.partner_id')
    horse_number = fields.Char(string='Horse Number', related='truck_id.horse_number')
    trailer_number = fields.Char(string='Trailer Number', related='truck_id.trailer_number')

    container_number = fields.Char(string='Container Number')
    driver_name = fields.Char(string='Driver Name')
    telephone_number = fields.Char(string='Telephone Number')

    seal_number = fields.Char(string='Seal Number')

    price = fields.Float(string='Price')
    max_load = fields.Float(string='Max. Load [kg]')
    price_per_kg = fields.Float(string='Price per Kg', compute='_compute_price_per_kg', digits=(4, 4), store=True)

    load_line_ids = fields.One2many('truck.route.line', 'truck_route_id', string='Load')
    truck_utilization = fields.Float(string='Truck Utilization (%)', compute='_compute_truck_utilization', store=True)

    available_product_ids = fields.One2many('product.product', string='Product', compute="_compute_available_products",
                                            store=False)
    available_location_ids = fields.One2many('stock.location', string='Locations',
                                             compute="_compute_available_locations", store=False)

    date_start = fields.Datetime(string='Start Date')
    date_end = fields.Datetime(string='End Date')

    approx_loading_time = fields.Float(string='Approx. Loading Time [hours]')
    approx_offloading_time = fields.Float(string='Approx. Offloading Time [hours]')

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

    @api.depends('load_line_ids.quantity', 'max_load')
    def _compute_truck_utilization(self):
        for record in self:
            total_allocated_quantity = sum(line.quantity * line.product_id.box_weight for line in record.load_line_ids)
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

    def allocate_product(self, product, unit_price, location_id, quantity, tax_ids):
        self.ensure_one()
        self.state = 'loaded'
        self.env['truck.route.line'].create({
            'truck_route_id': self.id,
            'product_id': product.id,
            'unit_price': unit_price,
            'location_id': location_id.id,
            'quantity': quantity,
            'tax_ids': [(6, 0, tax_ids.ids)],
        })

    def action_load_truck(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'truck.route',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'res_id': self.id
        }

    def action_create_invoice(self):
        if len(self.load_line_ids) == 0:
            raise exceptions.UserError(_("Please allocate products before creating an invoice."))
        if not self.seal_number:
            raise exceptions.UserError(_("Please enter the seal number before creating an invoice."))

        sale_order_id = self.meta_sale_order_id.create_sale_order_for_truck(self)
        self.meta_sale_order_id.create_invoice(sale_order_id)
        self.state = 'done'

    def action_handle_overload(self):
        truck_redistribution = self.env['redistribution.wizard'].create({
            'truck_route_id':
            self.id,
            'meta_sale_order_id':
            self.meta_sale_order_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'redistribution.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': truck_redistribution.id,
            'target': 'new',
            'context': {},
        }

    def _compute_available_products(self):
        for record in self:
            record.available_product_ids = record.meta_sale_order_id.order_line_ids.mapped('product_id')

    def _compute_available_locations(self):
        for record in self:
            record.available_location_ids = record.meta_sale_order_id.order_line_ids.mapped('location_id')

    @api.onchange('load_line_ids')
    def _update_state(self):
        for record in self:
            if len(record.load_line_ids) > 0:
                record.state = 'loaded'


class Truck(models.Model):
    _name = "truck"
    _description = "Truck"

    name = fields.Char(string="Truck", required=True, copy=False, readonly=False, index='trigram',
                       default=lambda self: default_name(self, prefix='T'))

    partner_id = fields.Many2one('res.partner', string="Transporter")
    horse_number = fields.Char(string='Horse Number')
    trailer_number = fields.Char(string='Trailer Number')

    truck_route_ids = fields.One2many('truck.route', 'truck_id', string='Truck Details')
