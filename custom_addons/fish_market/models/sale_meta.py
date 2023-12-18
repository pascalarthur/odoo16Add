from collections import defaultdict
from ..utils.model_utils import default_name
from odoo import models, fields, api, exceptions


META_SALE_STATES = [
    ('draft', 'Draft'),
    ('transport', 'Transport'),
    ('allocated', 'Allocated'),
    ('send_confirmations', 'Send Confirmations'),
    ('seal_trucks', 'Seal Trucks'),
    ('send_invoices', 'Send Invoices'),
    ('handle_overload', 'Handle Overload'),
    ('done', 'Done'),
]


class MetaSaleOrderLine(models.Model):
    _name = 'meta.sale.order.line'
    _description = 'Meta Sale Order Line'

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_weight = fields.Float('Product Weight [kg]', related='product_id.weight', store=True)
    unit_price = fields.Float('Unit Price', default=0.0)
    location_id = fields.Many2one('stock.location', string='Origin Location')
    quantity = fields.Float(string='Quantity', default=1.0)


class MetaSaleOrder(models.Model):
    _name = 'meta.sale.order'
    _description = 'Meta Sale Order'

    name = fields.Char(
        string="Meta Sale Reference",
        required=True, copy=False, readonly=False,
        index='trigram',
        default=lambda self: default_name(self, prefix='MS'))

    state = fields.Selection(META_SALE_STATES, string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer')

    order_line_ids = fields.One2many('meta.sale.order.line', 'meta_sale_order_id', string='Order Lines')
    transport_order_ids = fields.One2many('transport.order', 'meta_sale_order_id', string='Transport Orders')
    truck_ids = fields.One2many('truck.detail', 'meta_sale_order_id', string='Trucks')
    truck_ids_with_load = fields.One2many('truck.detail', compute='_compute_truck_ids_with_load')

    sale_order_ids = fields.One2many('sale.order', 'meta_sale_order_id', string='Sales Orders')

    container_demand = fields.Integer(string='Container Demand', compute='_compute_container_demand')

    @api.depends('order_line_ids')
    def _compute_container_demand(self):
        for record in self:
            total_weight = sum(line.quantity * line.product_id.weight for line in record.order_line_ids)
            record.container_demand = -(-total_weight // 35000) # ceil

    def _compute_truck_ids_with_load(self):
        for record in self:
            record.truck_ids_with_load = record.truck_ids.filtered(lambda t: t.load_line_ids)

    @api.model
    def get_warehouse(self, warehouse_id):
        return self.env['stock.warehouse'].search([('id', '=', warehouse_id.id)])

    def set_transport_state(self):
        self.ensure_one()
        if not self.partner_id:
            raise exceptions.UserError("Please select a customer first.")
        self.state = 'transport'

    def action_find_transporters(self):
        # Logic to find transporters
        logistic_partner_ids = self.env['res.partner'].search([('category_id.name', '=', 'Logistic')]).ids

        location_id = self.order_line_ids[0].location_id
        warehouse = self.get_warehouse(location_id.warehouse_id)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Route Supplier Communication',
            'view_mode': 'form',
            'res_model': 'route.demand.wizard',
            'view_id': self.env.ref('fish_market.view_route_demand_wizard_form').id,
            'target': 'new',  # Open the form in a new window
            'context': {
                'default_meta_sale_order_id': self.id,
                'default_partner_ids': logistic_partner_ids,
                'default_container_demand': self.container_demand,

                'default_route_start_street': warehouse.partner_id.street,
                'default_route_start_street2': warehouse.partner_id.street2,
                'default_route_start_zip': warehouse.partner_id.zip,
                'default_route_start_city': warehouse.partner_id.city,
                'default_route_start_state_id': warehouse.partner_id.state_id.id,
                'default_route_start_country_id': warehouse.partner_id.country_id.id,

                'default_route_end_street': self.partner_id.street,
                'default_route_end_street2': self.partner_id.street2,
                'default_route_end_zip': self.partner_id.zip,
                'default_route_end_city': self.partner_id.city,
                'default_route_end_state_id': self.partner_id.state_id.id,
                'default_route_end_country_id': self.partner_id.country_id.id,
            },
        }

    def action_allocate_transporters(self):

        # Step 1: Raise a warning if no transporter replied yet
        if not self.transport_order_ids or not any(self.transport_order_ids.mapped('truck_ids')):
            raise exceptions.UserError("No transport offers have been received yet.")

        # Step 2: Clear existing allocations
        for transport_order in self.transport_order_ids:
            for truck in transport_order.truck_ids:
                # Assuming truck.load_line_ids is the One2many field linking to TruckLoadLine
                truck.load_line_ids.unlink()  # This will delete the TruckLoadLine records

        # Step 3: Proceed with new allocations
        for order_line in self.order_line_ids:
            product = order_line.product_id
            location_id = order_line.location_id

            required_quantity = order_line.quantity # Assuming 'quantity' is the correct field
            allocated_quantity = 0.0

            for transport_order in self.transport_order_ids:
                trucks = transport_order.truck_ids.sorted(key=lambda t: t.price_per_kg)
                for truck in trucks:
                    if allocated_quantity >= required_quantity:
                        break

                    # Assuming 'max_load' represents the capacity and there's a field to track allocated capacity
                    available_capacity = truck.max_load - sum(line.quantity * line.product_id.weight for line in truck.load_line_ids)
                    available_capacity = available_capacity // product.weight  # Convert to product quantity

                    # It is only worthwile to pick up 10 boxes or more
                    if available_capacity > 10:
                        quantity_to_allocate = min(required_quantity - allocated_quantity, available_capacity)
                        truck.allocate_product(product, order_line.unit_price, location_id, quantity_to_allocate)
                        allocated_quantity += quantity_to_allocate

        self.ensure_one()
        self.state = 'allocated'

        return True

    def action_send_confirmations(self):
        template = self.env.ref('fish_market.email_template')
        my_company_email = self.env.user.company_id.email

        # Send confirmation to transporters
        for transport_order in self.transport_order_ids:
            transporter_email = transport_order.partner_id.email
            if transporter_email:
                for truck in transport_order.truck_ids:
                    if len(truck.load_line_ids) > 0:
                        email_values = {
                            'email_to': transporter_email,
                            'email_from': my_company_email,
                            'subject': 'Transport Order Confirmation',
                            'body_html': self._prepare_email_content_for_transporter(truck),
                        }
                        template.send_mail(self.id, email_values=email_values, force_send=True)

        location_load_map = defaultdict(list)
        for transport_order in self.transport_order_ids:
            for truck in transport_order.truck_ids:
                for load_line in truck.load_line_ids:
                    location_load_map[load_line.location_id].append(load_line)

        for location_id, lines in location_load_map.items():
            warehouse_id = self.get_warehouse(location_id.warehouse_id)
            supplier_email = warehouse_id.partner_id.email  # Assuming location has a related partner (supplier)
            if supplier_email:
                email_values = {
                    'email_to': supplier_email,
                    'email_from': my_company_email,
                    'subject': 'Product Collection Confirmation',
                    'body_html': self._prepare_email_content_for_supplier_at_location(warehouse_id, location_id, lines),
                }
                template.send_mail(self.id, email_values=email_values, force_send=True)

        self.ensure_one()
        self.state = 'seal_trucks'

    def _prepare_email_content_for_transporter(self, truck):
        # Prepare the email content for the transporter
        content = f"Dear {truck.transport_order_id.partner_id.name},<br/>"
        content += f"You are selected to pick up the following products:<br/>"
        for line in truck.load_line_ids:
            content += f"Product: {line.product_id.name}, Quantity: {line.quantity}, Location: {line.location_id.name}<br/>"
        return content

    def _prepare_email_content_for_supplier_at_location(self, warehouse_id, location, lines):
        content = f"Dear {warehouse_id.partner_id.name},<br/>"
        content += f"The following products are scheduled to be picked up from your location ({location.name}):<br/>"
        for line in lines:
            truck = line.truck_detail_id
            content += f"Truck {truck.truck_number} will pick up: Product {line.product_id.name}, Quantity: {line.quantity}<br/>"
        return content

    def action_confirm_seals(self):
        self.ensure_one()
        for truck_id in self.truck_ids_with_load:
            if not truck_id.seal_number:
                raise exceptions.UserError(f"Please enter a seal number for truck {truck_id.name}")
        self.state = 'send_invoices'
        self.action_send_invoices()

    def action_send_invoices(self):
        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']

        for transport_order in self.transport_order_ids:
            for truck in transport_order.truck_ids:
                if len(truck.load_line_ids) > 0:
                    # Create a sale order for each truck
                    sale_order_vals = {
                        'meta_sale_order_id': self.id,
                        'partner_id': self.partner_id.id,
                        'truck_detail_id': truck.id,
                        # Add other necessary fields and values
                    }
                    sale_order = SaleOrder.create(sale_order_vals)

                    for load_line in truck.load_line_ids:
                        sale_order_line_vals = {
                            'order_id': sale_order.id,
                            'product_id': load_line.product_id.id,
                            'product_uom_qty': load_line.quantity,
                            'price_unit': load_line.unit_price,
                            # Ensure to include other necessary fields like product_uom, price_unit, etc.
                        }
                        SaleOrderLine.create(sale_order_line_vals)
                    sale_order.action_quotation_send_programmatically()
        self.state = 'handle_overload'

    def action_set_done(self):
        self.ensure_one()
        self.state = 'done'

    def stay_on_dialog(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'meta.sale.order',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'},
        }
