from odoo import models, fields

class QuotationManagement(models.Model):
    _name = 'quotation.management'
    _description = 'Quotation Management'

    name = fields.Char(string='Reference', required=True)
    stage = fields.Selection([
        ('quotations', 'Quotations'),
        ('transports', 'Transports'),
        ('sealing', 'Sealing'),
        ('arrival', 'Arrival')
    ], string='Stage', default='quotations')
    purchase_order_ids = fields.One2many(
        'purchase.order', 'quotation_management_id', string='Quotations')
