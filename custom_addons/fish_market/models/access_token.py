from odoo import models, fields
import secrets

class AccessToken(models.Model):
    _name = 'access.token'
    _description = 'Access Token'

    partner_id = fields.Many2one('res.partner', string='Supplier', required=True)
    expiry_date = fields.Datetime('Expiry Date', required=True)
    transport_order_id = fields.Many2one('transport.order', string='Transport Order', required=True)

    token = fields.Char('Token', required=True, default=lambda self: secrets.token_urlsafe(16))
    is_used = fields.Boolean('Used', default=False)
