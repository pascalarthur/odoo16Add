from collections import defaultdict
from ..utils.model_utils import default_name
from odoo import models, fields, api, exceptions

META_SALE_STATES = [
    ('draft', 'Draft'),
    ('transport', 'Transport'),
    ('allocated', 'Allocated'),
    ('send_confirmations', 'Send Confirmations'),
    ('seal_trucks', 'Seal Trucks'),
    ('send_invoice', 'Invoice'),
    ('handle_overload', 'Handle Overload'),
    ('done', 'Done'),
]


class MetaSaleOrderLine(models.Model):
    _name = 'meta.sale.order.line'
    _description = 'Meta Sale Order Line'

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    box_weight = fields.Float('Box Weight [kg]', related='product_id.box_weight', store=True)
    unit_price = fields.Float('Unit Price', default=0.0)
    location_id = fields.Many2one('stock.location', string='Origin Location')
    quantity = fields.Float(string='Quantity', default=1.0)


class MetaSaleOrder(models.Model):
    _name = 'meta.sale.order'
    _description = 'Meta Sale Order'

    name = fields.Char(string="Meta Sale Reference", required=True, copy=False, readonly=False, index='trigram',
                       default=lambda self: default_name(self, prefix='MS'))

    state = fields.Selection(META_SALE_STATES, string='Status', readonly=True, index=True, copy=False, default='draft')
    partner_id = fields.Many2one('res.partner', string='Customer')

    transport_product_id = fields.Many2one('product.template', string='Transport Route',
                                           domain=[('type', '=', 'transport')], required=True)
    transport_pricelist_id = fields.Many2one('product.pricelist', string='Transport Pricelist', required=True)
    transport_pricelist_item_ids = fields.One2many('product.pricelist.item', 'meta_sale_order_id',
                                                   string='Transport Bids with Backloads')
    transport_pricelist_item_ids_no_backload = fields.One2many(
        'product.pricelist.item', compute='_compute_transport_pricelist_item_ids_no_backload', string='Transport Bids')
    container_demand = fields.Integer(string='Container Demand', compute='_compute_container_demand')

    transport_pricelist_backloads_count = fields.Integer(compute='_compute_transport_pricelist_backloads_count')

    order_line_ids = fields.One2many('meta.sale.order.line', 'meta_sale_order_id', string='Order Lines')
    truck_ids = fields.One2many('truck.detail', 'meta_sale_order_id', string='All Trucks')
    truck_ids_no_backload = fields.One2many('truck.detail', string='Trucks', compute='_compute_truck_ids_no_backload',
                                            readonly=False)

    sale_order_ids = fields.One2many('sale.order', 'meta_sale_order_id', string='Sales Orders', readonly=True)
    invoice_ids = fields.Many2many('account.move', string='Invoices', related='sale_order_ids.invoice_ids',
                                   readonly=True)

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    def _compute_truck_ids_no_backload(self):
        for record in self:
            record.truck_ids_no_backload = record.truck_ids.filtered(lambda t: not t.is_backload)

    def _compute_transport_pricelist_backloads_count(self):
        for record in self:
            record.transport_pricelist_backloads_count = len(record.transport_pricelist_item_ids.mapped('backload_id'))

    @api.depends('order_line_ids')
    def _compute_container_demand(self):
        for record in self:
            total_weight = sum(line.quantity * line.product_id.box_weight for line in record.order_line_ids)
            record.container_demand = -(-total_weight // 35000)  # ceil

    @api.depends('transport_pricelist_item_ids')
    def _compute_transport_pricelist_item_ids_no_backload(self):
        for record in self:
            record.transport_pricelist_item_ids_no_backload = record.transport_pricelist_item_ids.filtered(
                lambda t: not t.is_backload)

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

        start_warehouse_id = self.transport_product_id.start_warehouse_id
        destination_warehouse_id = self.transport_product_id.destination_warehouse_id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Route Supplier Communication',
            'view_mode': 'form',
            'res_model': 'route.demand',
            'view_id': self.env.ref('fish_market.view_route_demand_form').id,
            'target': 'new',  # Open the form in a new window
            'context': {
                'default_meta_sale_order_id': self.id,
                'default_partner_ids': logistic_partner_ids,
                'default_container_demand': self.container_demand,
                'default_start_date': self.start_date,
                'default_end_date': self.end_date,
                'default_route_start_street': start_warehouse_id.partner_id.street,
                'default_route_start_street2': start_warehouse_id.partner_id.street2,
                'default_route_start_zip': start_warehouse_id.partner_id.zip,
                'default_route_start_city': start_warehouse_id.partner_id.city,
                'default_route_start_state_id': start_warehouse_id.partner_id.state_id.id,
                'default_route_start_country_id': start_warehouse_id.partner_id.country_id.id,
                'default_route_end_street': destination_warehouse_id.partner_id.street,
                'default_route_end_street2': destination_warehouse_id.partner_id.street2,
                'default_route_end_zip': destination_warehouse_id.partner_id.zip,
                'default_route_end_city': destination_warehouse_id.partner_id.city,
                'default_route_end_state_id': destination_warehouse_id.partner_id.state_id.id,
                'default_route_end_country_id': destination_warehouse_id.partner_id.country_id.id,
            },
        }

    def action_allocate_transporters(self):
        # Step 1: Raise a warning if no transporter replied yet
        if not self.truck_ids_no_backload:
            raise exceptions.UserError("No transport offers have been received yet.")

        # Step 2: Clear existing allocations
        for truck_id in self.truck_ids:
            truck_id.load_line_ids.unlink()  # This will delete the TruckLoadLine records

        # Step 3: Proceed with new allocations
        for order_line in self.order_line_ids:
            product = order_line.product_id
            if product.box_weight == 0.0:
                raise exceptions.UserError(f"Please specify a box weight for product: {product.display_name}")

            required_quantity = order_line.quantity  # Assuming 'quantity' is the correct field
            allocated_quantity = 0.0
            truck_ids = self.truck_ids_no_backload.sorted(key=lambda t: t.price_per_kg)
            for truck_id in truck_ids:
                if allocated_quantity >= required_quantity:
                    break

                # Assuming 'max_load' represents the capacity and there's a field to track allocated capacity
                available_capacity = truck_id.max_load - sum(line.quantity * line.product_id.box_weight
                                                             for line in truck_id.load_line_ids)
                available_capacity = available_capacity // product.box_weight  # Convert to product quantity

                # It is only worthwile to pick up 10 boxes or more
                if available_capacity > 10:
                    quantity_to_allocate = min(required_quantity - allocated_quantity, available_capacity)
                    truck_id.allocate_product(product, order_line.unit_price, order_line.location_id,
                                              quantity_to_allocate)
                    allocated_quantity += quantity_to_allocate

        self.ensure_one()
        self.state = 'allocated'

        return True

    def action_send_confirmations(self):
        template = self.env.ref('fish_market.email_template')
        my_company_email = self.env.user.company_id.email

        # Send confirmation to transporters
        for truck_id in self.truck_ids_no_backload.filtered(lambda t: len(t.load_line_ids) > 0):
            transporter_email = truck_id.partner_id.email
            if transporter_email:
                email_values = {
                    'email_to': transporter_email,
                    'email_from': my_company_email,
                    'subject': 'Transport Order Confirmation',
                    'body_html': self._prepare_email_content_for_transporter(truck_id),
                }
                template.send_mail(self.id, email_values=email_values, force_send=True)

        location_load_map = defaultdict(list)
        for truck_id in self.truck_ids_no_backload.filtered(lambda t: len(t.load_line_ids) > 0):
            for load_line in truck_id.load_line_ids:
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
        self.action_send_order_confirmation()

    def _prepare_email_content_for_transporter(self, truck):
        # Prepare the email content for the transporter
        content = f"Dear {truck.partner_id.name},<br/>"
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

    def action_send_order_confirmation(self):
        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']

        for truck_id in self.truck_ids_no_backload.filtered(lambda t: len(t.load_line_ids) > 0):
            # Create a sale order for each truck
            sale_order = SaleOrder.create({
                'meta_sale_order_id': self.id,
                'partner_id': self.partner_id.id,
                'truck_detail_id': truck_id.id,
                'truck_number': truck_id.truck_number,
                'horse_number': truck_id.horse_number,
                'container_number': truck_id.container_number,
                'seal_number': truck_id.seal_number,
                'driver_name': truck_id.driver_name,
                'telephone_number': truck_id.telephone_number,
            })

            for load_line in truck_id.load_line_ids:
                SaleOrderLine.create({
                    'order_id': sale_order.id,
                    'product_id': load_line.product_id.id,
                    'product_uom_qty': load_line.quantity,
                    'price_unit': load_line.unit_price,
                })
            sale_order.action_quotation_send_programmatically()
            sale_order.state = 'sent'

        self.state = 'seal_trucks'

    def action_confirm_seals(self):
        self.ensure_one()
        for truck_id in self.truck_ids_no_backload.filtered(lambda t: len(t.load_line_ids) > 0):
            if not truck_id.seal_number:
                raise exceptions.UserError(f"Please enter a seal number for truck {truck_id.name}")
        self.state = 'send_invoice'

    def action_send_invoice(self):
        self.ensure_one()
        for sale_id in self.sale_order_ids:
            if sale_id.state in ['draft', 'sent']:
                sale_id.action_confirm()
                if sale_id.invoice_status != 'invoiced':
                    invoice = sale_id._create_invoices()
                    invoice.action_post()
        self.state = 'handle_overload'

    def action_set_done(self):
        self.ensure_one()
        self.state = 'done'

    def action_add_truck(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Truck',
            'view_mode': 'form',
            'res_model': 'truck.detail',
            'target': 'new',
            'context': {
                'default_meta_sale_order_id': self.id,
            },
        }

    def action_view_optional_backloads(self):
        self.ensure_one()
        active_transport_ids = self.transport_pricelist_item_ids
        backload_filtered_ids = active_transport_ids.mapped('backload_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Optional Backloads',
            'view_mode': 'tree,form',
            'res_model': 'product.pricelist.item',
            'domain': [('id', 'in', backload_filtered_ids), ('meta_sale_order_id', '=', self.id)],
            'target': 'current',
        }
