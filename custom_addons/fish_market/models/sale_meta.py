from odoo import models, fields, api


class MetaSaleOrderLine(models.Model):
    _name = 'meta.sale.order.line'
    _description = 'Meta Sale Order Line'

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    location_id = fields.Many2one('stock.location', string='Origin Location')
    quantity = fields.Float(string='Quantity', default=1.0)


class MetaSaleOrder(models.Model):
    _name = 'meta.sale.order'
    _description = 'Meta Sale Order'

    name = fields.Char(string='Reference', required=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('transport', 'Transport'),
        ('optional_storage', 'Optional Storage'),
        ('send_confirmation', 'Send Confirmation'),
        ('notify_suppliers', 'Notify Suppliers'),
        ('seal_trucks', 'Seal Trucks'),
        ('send_invoices', 'Send Invoices'),
        ('handle_overload', 'Handle Overload')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer')

    sale_order_ids = fields.One2many('sale.order', 'meta_sale_order_id', string='Sales Orders')
    order_line_ids = fields.One2many('meta.sale.order.line', 'meta_sale_order_id', string='Order Lines')
    transport_order_ids = fields.One2many('transport.order', 'meta_sale_order_id', string='Transport Orders')


    @api.model
    def get_warehouse(self, warehouse_id):
        Warehouse = self.env['stock.warehouse']
        return Warehouse.search([('id', '=', warehouse_id.id)])

    def action_find_transporters(self):
        # Logic to find transporters
        logistic_partner_ids = self.env['res.partner'].search([('category_id.name', '=', 'Logistic')]).ids

        location_id = self.order_line_ids[0].location_id
        warehouse = self.get_warehouse(location_id.warehouse_id)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Route Supplier Communication',
            'view_mode': 'form',
            'res_model': 'route.demand',
            'view_id': self.env.ref('fish_market.view_route_supplier_communication_form').id,
            'target': 'new',  # Open the form in a new window
            'context': {
                'default_meta_sale_order_id': self.id,
                'default_partner_ids': logistic_partner_ids,

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
        # Logic to allocate transporters
        pass

    def set_transport_state(self):
        self.ensure_one()
        self.state = 'transport'
        return self.stay_on_dialog()

    def set_seal_state(self):
        # Change state to 'seal'
        self.ensure_one()
        self.state = 'seal'
        return self.stay_on_dialog()

    def set_sent_state(self):
        # Change state to 'seal'
        self.ensure_one()
        self.state = 'sent'
        return self.stay_on_dialog()

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
