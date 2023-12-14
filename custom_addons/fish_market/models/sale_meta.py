from odoo import models, fields, api

class MetaSaleOrder(models.Model):
    _name = 'meta.sale.order'
    _description = 'Meta Sale Order'

    name = fields.Char(string='Reference', required=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('find_transporters', 'Find Transporters'),
        ('allocate_transporters', 'Allocate Transporters'),
        ('optional_storage', 'Optional Storage'),
        ('send_confirmation', 'Send Confirmation'),
        ('notify_suppliers', 'Notify Suppliers'),
        ('seal_trucks', 'Seal Trucks'),
        ('send_invoices', 'Send Invoices'),
        ('handle_overload', 'Handle Overload')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    sale_order_ids = fields.One2many('sale.order', 'meta_sale_order_id', string='Sales Orders')

    def action_find_transporters(self):
        # Logic to find transporters
        self.state = 'find_transporters'

    def action_allocate_transporters(self):
        # Logic to allocate transporters
        self.state = 'allocate_transporters'
