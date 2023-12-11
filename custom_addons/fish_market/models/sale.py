from odoo import api, models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection([('draft', 'Quotation'), ('transport', 'Transport'), ('seal', 'Seal'), ('sent', 'Quotation Sent'), ('sale', 'Sales Order')])

    seal_number = fields.Char(string='Seal Number')
    transport_company_ids = fields.Many2many('res.partner', string='Transport Companies')

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

    def action_find_transport(self):
        # Assuming the model of the new form is 'route.supplier.communication'
        # and the ID of the form view is 'view_route_supplier_communication_form'
        logistic_partner_ids = self.env['res.partner'].search([('category_id.name', '=', 'Logistic')]).ids

        action = {
            'type': 'ir.actions.act_window',
            'name': 'Route Supplier Communication',
            'view_mode': 'form',
            'res_model': 'route.demand',
            'view_id': self.env.ref('fish_market.view_route_supplier_communication_form').id,
            'target': 'new',  # Open the form in a new window
            'context': {
                'default_supplier_ids': logistic_partner_ids,
            },
        }
        return action

    def set_transport_state(self):
        self.ensure_one()
        self.state = 'transport'

    def set_seal_state(self):
        # Change state to 'seal'
        self.ensure_one()
        self.state = 'seal'


    def set_sent_state(self):
        # Change state to 'seal'
        self.ensure_one()
        self.state = 'sent'