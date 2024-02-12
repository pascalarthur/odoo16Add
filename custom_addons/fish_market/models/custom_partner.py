from odoo import fields, models

class CustomPartner(models.Model):
    _inherit = 'res.partner'

    def send_action_email_bid_suppliers(self, pricelist_id=None):
        if pricelist_id is None:
            return {
                'name': 'Select Pricelist',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'supplier.price.wizard',
                'target': 'new',
                'context': {
                    'default_logistic_partner_ids': self.ids,
                    'default_pricelist_id': self.env['product.pricelist'].search([], limit=1).id
                }
            }
