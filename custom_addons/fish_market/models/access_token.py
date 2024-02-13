from odoo import models, fields
import secrets

class AccessToken(models.Model):
    _name = 'access.token'
    _description = 'Access Token'

    partner_id = fields.Many2one('res.partner', string='Supplier', required=True, ondelete='cascade')
    expiry_date = fields.Datetime('Expiry Date', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')

    route_demand_id = fields.Many2one('route.demand', string='Route Demand')
    product_pricelist_item_ids = fields.Many2many('product.pricelist.item', string='Product Offers')

    token = fields.Char('Token', required=True, default=lambda self: secrets.token_urlsafe(16))
    is_used = fields.Boolean('Used', default=False)

    detailed_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product'),
        ('transport', 'Transport')], string='Product Type', default='product', required=True)
