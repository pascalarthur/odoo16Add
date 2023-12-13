from odoo import api, models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection([('draft', 'Quotation'), ('transport', 'Transport'), ('seal', 'Seal'), ('sent', 'Quotation Sent'), ('sale', 'Sales Order')])

    seal_number = fields.Char(string='Seal Number')
    transport_company_ids = fields.Many2many('res.partner', string='Transport Companies')
    location_id = fields.Many2one('stock.location', string='Origin Location')

    @api.model
    def check_and_delete_order(self, order_id, creation_date):
        order = self.browse(order_id)
        # Check if the order was not modified (you might need to adjust this logic)
        if order.create_date == fields.Datetime.from_string(creation_date):
            order.unlink()  # Delete the order

    @api.model
    def create(self, vals):
        # You can set a default stage here if needed
        return super(SaleOrder, self).create(vals)

    @api.model
    def get_warehouse(self, warehouse_id):
        Warehouse = self.env['stock.warehouse']
        return Warehouse.search([('id', '=', warehouse_id.id)])

    def action_find_transport(self):
        # Assuming the model of the new form is 'route.supplier.communication'
        # and the ID of the form view is 'view_route_supplier_communication_form'
        logistic_partner_ids = self.env['res.partner'].search([('category_id.name', '=', 'Logistic')]).ids

        self.partner_id.contact_address
        warehouse = self.get_warehouse(self.location_id.warehouse_id)

        action = {
            'type': 'ir.actions.act_window',
            'name': 'Route Supplier Communication',
            'view_mode': 'form',
            'res_model': 'route.demand',
            'view_id': self.env.ref('fish_market.view_route_supplier_communication_form').id,
            'target': 'new',  # Open the form in a new window
            'context': {
                'default_supplier_ids': logistic_partner_ids,

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
        return action

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
            'res_model': 'sale.order',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'},
        }