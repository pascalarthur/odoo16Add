from odoo import fields, models


class CustomPartner(models.Model):
    _inherit = 'res.partner'

    def send_action_email_bid_suppliers(self, pricelist_id=None):
        return {
            'name': 'Pricelist Wizard',
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_id': self.env.ref('fish_market.view_pricelist_wizard_form').id,
            'view_mode': 'form',
            'res_model': 'supplier.price.wizard',
            'target': 'new',
            'context': {
                'default_logistic_partner_ids': self.ids,
                'default_pricelist_id': self.env['product.pricelist'].search([], limit=1).id
            }
        }
