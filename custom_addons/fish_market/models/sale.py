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
        # You can set a default stage here if needed
        print('action_find_transport')

    def action_seal(self):
        # You can set a default stage here if needed
        print('action_seal')