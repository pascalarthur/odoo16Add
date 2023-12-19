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
                'context': {'default_pricelist_id': self.env['product.pricelist'].search([], limit=1).id}
            }


    def send_action_email_bid_logistics(self):
        partners = self.env['res.partner'].browse(self._context.get('active_ids', []))
        template = self.env.ref('fish_market.email_template_logistic')

        for partner in partners:
            if not partner.email:
                raise Exception("Partner '%s' has no email address." % partner.name)
            template.send_mail(partner.id, force_send=True)


