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
    box_weight = fields.Float('Box Weight [kg]', related='product_id.box_weight', store=True, readonly=True)
    unit_price = fields.Float('Unit Price', required=True)
    location_id = fields.Many2one('stock.location', string='Origin Location')
    quantity = fields.Float(string='Quantity', default=1.0)
    tax_ids = fields.Many2many('account.tax', string='Taxes')


class MetaSaleOrder(models.Model):
    _name = 'meta.sale.order'
    _description = 'Meta Sale Order'

    name = fields.Char(string="Meta Sale Reference", required=True, copy=False, readonly=False, index='trigram',
                       default=lambda self: default_name(self, prefix='MS'))

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        compute='_compute_company_id',
        inverse='_inverse_company_id',
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )

    state = fields.Selection(META_SALE_STATES, string='Status', readonly=True, index=True, copy=False, default='draft')
    partner_id = fields.Many2one('res.partner', string='Customer')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True)
    partner_bank_id = fields.Many2one(
        'res.partner.bank',
        string='Recipient Bank',
        store=True,
        readonly=False,
        help="Bank Account Number to which the invoice will be paid. "
        "A Company bank account if this is a Customer Invoice or Vendor Credit Note, "
        "otherwise a Partner bank account number.",
        check_company=True,
    )

    transport_product_id = fields.Many2one('product.template', string='Transport Route',
                                           domain=[('type', '=', 'transport')], required=True)
    transport_pricelist_id = fields.Many2one('product.pricelist', string='Transport Pricelist', required=True)
    transport_pricelist_item_ids = fields.One2many('product.pricelist.item', 'meta_sale_order_id',
                                                   string='Transport Bids with Backloads')
    transport_pricelist_item_ids_no_backload = fields.One2many(
        'product.pricelist.item', compute='_compute_transport_pricelist_item_ids_no_backload', string='Transport Bids')
    container_demand = fields.Integer(string='Container Demand', compute='_compute_container_demand')

    transport_backloads_count = fields.Integer(compute='_compute_transport_backloads_count')

    order_line_ids = fields.One2many('meta.sale.order.line', 'meta_sale_order_id', string='Order Lines')
    truck_route_ids = fields.One2many('truck.route', 'meta_sale_order_id', string='All Trucks')
    truck_route_ids_no_backload = fields.One2many('truck.route', string='Trucks',
                                                  compute='_compute_truck_route_ids_no_backload', readonly=False)

    extra_products_on_truck_ids = fields.Many2many('product.product', string='Extra Products')

    sale_order_ids = fields.One2many('sale.order', 'meta_sale_order_id', string='Sales Orders', readonly=True)
    sale_order_count = fields.Integer(string='Sale Orders', compute='_compute_sale_order_count', store=True)
    invoice_ids = fields.Many2many('account.move', string='Invoices', compute='_compute_invoice_ids', store=True,
                                   readonly=True)

    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)

    @api.depends('sale_order_ids')
    def _compute_sale_order_count(self):
        for record in self:
            record.sale_order_count = len(record.sale_order_ids)

    @api.depends('sale_order_ids')
    def _compute_invoice_ids(self):
        for record in self:
            record.invoice_ids = record.sale_order_ids.mapped('invoice_ids')

    def _compute_company_id(self):
        for meta_sale in self:
            meta_sale.company_id = meta_sale.partner_id.company_id

    def _compute_truck_route_ids_no_backload(self):
        for record in self:
            record.truck_route_ids_no_backload = record.truck_route_ids.filtered(lambda t: not t.is_backload)

    def _compute_transport_backloads_count(self):
        for record in self:
            record.transport_backloads_count = len(record.transport_pricelist_item_ids.mapped('backload_id'))

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

    @api.onchange('transport_product_id')
    def _onchange_extra_products_on_truck_ids(self):
        for record in self:
            if record.transport_product_id:
                if record.transport_product_id.sh_is_bundle:
                    for sh_bundle_product_id in record.transport_product_id.sh_bundle_product_ids:
                        record.extra_products_on_truck_ids = [(4, sh_bundle_product_id.sh_product_id.id)]
                else:
                    one_way_variant_id = record.transport_product_id.product_variant_ids[0]
                    record.extra_products_on_truck_ids = [(4, one_way_variant_id.id)]

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
                'default_date_start': self.date_start,
                'default_date_end': self.date_end,
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
        if not self.truck_route_ids_no_backload:
            raise exceptions.UserError("No transport offers have been received yet.")

        # Step 2: Raise a warning if no transport offers have been accepted yet
        if not self.truck_route_ids_no_backload.filtered(lambda t: t.state != 'draft'):
            raise exceptions.UserError(
                "No transport offers have been accepted yet. Please confirm bids/add trucks manually.")

        # Step 2: Clear existing allocations
        for truck_route_id in self.truck_route_ids_no_backload.filtered(lambda t: t.state not in ['draft', 'done']):
            truck_route_id.load_line_ids.unlink()  # This will delete the TruckLoadLine records
            truck_route_id.state = 'confirmed'

        truck_route_ids = self.truck_route_ids_no_backload.filtered(lambda t: t.state == 'confirmed').sorted(
            key=lambda t: t.price_per_kg)
        # Step 3: Proceed with new allocations
        for order_line in self.order_line_ids:
            product = order_line.product_id
            if product.box_weight == 0.0:
                raise exceptions.UserError(f"Please specify a box weight for product: {product.display_name}")

            required_quantity = order_line.quantity  # Assuming 'quantity' is the correct field
            allocated_quantity = 0.0

            for truck_route_id in truck_route_ids:
                if allocated_quantity >= required_quantity:
                    break

                # Assuming 'max_load' represents the capacity and there's a field to track allocated capacity
                available_capacity = truck_route_id.max_load - sum(line.quantity * line.product_id.box_weight
                                                                   for line in truck_route_id.load_line_ids)
                available_capacity = available_capacity // product.box_weight  # Convert to product quantity

                # It is only worthwile to pick up 10 boxes or more
                if available_capacity > 10:
                    quantity_to_allocate = min(required_quantity - allocated_quantity, available_capacity)
                    truck_route_id.allocate_product(product, order_line.unit_price, order_line.location_id,
                                                    quantity_to_allocate, order_line.tax_ids)
                    allocated_quantity += quantity_to_allocate

        self.ensure_one()
        self.state = 'allocated'

        return True

    def action_send_confirmations(self):
        template = self.env.ref('fish_market.email_template')
        my_company_email = self.env.user.company_id.email

        # Send confirmation to transporters
        for truck_route_id in self.truck_route_ids_no_backload.filtered(lambda t: len(t.load_line_ids) > 0):
            transporter_email = truck_route_id.partner_id.email
            if transporter_email:
                email_values = {
                    'email_to': transporter_email,
                    'email_from': my_company_email,
                    'subject': 'Transport Order Confirmation',
                    'body_html': self._prepare_email_content_for_transporter(truck_route_id),
                }
                template.send_mail(self.id, email_values=email_values, force_send=True)

        location_load_map = defaultdict(list)
        for truck_route_id in self.truck_route_ids_no_backload.filtered(lambda t: len(t.load_line_ids) > 0):
            for load_line in truck_route_id.load_line_ids:
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

    def _get_warehouse_address(self, warehouse_id) -> str:
        address = []
        for attr in ['street', 'street2', 'zip', 'city', 'state_id', 'country_id']:
            if warehouse_id.partner_id[attr]:
                if attr.endswith('_id'):
                    address.append(warehouse_id.partner_id[attr].name)
                else:
                    address.append(warehouse_id.partner_id[attr])
        return ', '.join(address)

    def _prepare_email_content_for_transporter(self, truck):
        # Prepare the email content for the transporter
        warehouse_id = self.transport_product_id.start_warehouse_id
        address = self._get_warehouse_address(warehouse_id)

        content = f"Dear {truck.partner_id.name},<br/>"
        content += f"You are selected to pick up the following products:<br/>"
        content += "<table style='border-collapse: collapse; text-align: left'>"
        header = "".join([
            "<th style='border: 1px solid black;'>" + x + "</th>"
            for x in ["Product", "Quantity", "Address", "Address - Ref"]
        ])
        content += f"<strong><tr style='border: 1px solid black;'>{header}</tr></strong>"
        for line in truck.load_line_ids:
            address_ref = f"{line.location_id.location_id.name}/{line.location_id.name} ({warehouse_id.name})"
            content_line = "".join([
                f"<td style='border: 1px solid black;'>{x}</td>"
                for x in [line.product_id.name, line.quantity, address, address_ref]
            ])
            content += f"<tr style='border: 1px solid black;'>{content_line}</tr>"
        content += "</table>"
        return content

    def _prepare_email_content_for_supplier_at_location(self, warehouse_id, location, lines):
        content = f"Dear {warehouse_id.partner_id.name},<br/>"
        content += f"The following products are scheduled to be picked up from your location ({location.name}):<br/>"
        for line in lines:
            truck = line.truck_route_id
            content += f"Truck {truck.trailer_number} will pick up: Product {line.product_id.name}, Quantity: {line.quantity}<br/>"
        return content

    def _attach_sale_and_purchase_to_truck_route(self, sale_order):
        sale_order.truck_route_id.sale_id = sale_order
        sale_order.truck_route_id.purchase_id = sale_order.inter_transfer_id.purchase_id

    def create_sale_order_for_truck(self, truck_route_id):
        sale_order_id = self.env['sale.order'].create({
            'meta_sale_order_id': self.id,
            'partner_id': self.partner_id.id,
            'truck_route_id': truck_route_id.id,
            'trailer_number': truck_route_id.trailer_number,
            'horse_number': truck_route_id.horse_number,
            'container_number': truck_route_id.container_number,
            'driver_name': truck_route_id.driver_name,
            'telephone_number': truck_route_id.telephone_number,
            'pricelist_id': self.pricelist_id.id,
        })

        for load_line in truck_route_id.load_line_ids:
            self.env['sale.order.line'].create({
                'order_id': sale_order_id.id,
                'product_id': load_line.product_id.id,
                'product_uom_qty': load_line.quantity,
                'price_unit': load_line.unit_price,
                'tax_id': [(6, 0, load_line.tax_ids.ids)],
            })

        for product_id in self.extra_products_on_truck_ids:
            self.env['sale.order.line'].create({
                'order_id': sale_order_id.id,
                'product_id': product_id.id,
                'product_uom_qty': 1,
                'price_unit': product_id.list_price,
            })

        sale_order_id.action_quotation_send_programmatically()
        self._attach_sale_and_purchase_to_truck_route(sale_order_id)
        sale_order_id.state = 'sent'
        return sale_order_id

    def action_send_order_confirmation(self):
        for truck_route_id in self.truck_route_ids_no_backload.filtered(lambda t: len(t.load_line_ids) > 0):
            # Check that we do not have created the invoice yet
            if truck_route_id.id not in self.sale_order_ids.mapped('truck_route_id').ids:
                self.create_sale_order_for_truck(truck_route_id)
        self.state = 'seal_trucks'

    def action_confirm_seals(self):
        self.ensure_one()
        for truck_route_id in self.truck_route_ids_no_backload.filtered(lambda t: len(t.load_line_ids) > 0):
            if not truck_route_id.seal_number:
                raise exceptions.UserError(f"Please enter a seal number for truck {truck_route_id.name}")
        self.state = 'send_invoice'

    def create_invoice(self, sale_id) -> None:
        if sale_id.state in ['draft', 'sent']:
            sale_id.action_confirm()
            if sale_id.invoice_status != 'invoiced':
                invoice_id = sale_id._create_invoices()
                invoice_id.action_post()
            for invoice_id in sale_id.invoice_ids:
                invoice_id.write({
                    'partner_bank_id': self.partner_bank_id.id,
                    'seal_number': sale_id.truck_route_id.seal_number
                })
        self._attach_sale_and_purchase_to_truck_route(sale_id)

    def action_send_invoice(self):
        self.ensure_one()
        for sale_id in self.sale_order_ids:
            self.create_invoice(sale_id)
        self.state = 'handle_overload'

    def action_set_done(self):
        self.ensure_one()
        self.state = 'done'

    def action_add_truck_route(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Truck',
            'view_mode': 'form',
            'res_model': 'truck.route',
            'target': 'new',
            'context': {
                'default_meta_sale_order_id': self.id,
                'default_state': 'confirmed',
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
