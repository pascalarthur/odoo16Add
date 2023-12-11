from odoo import fields, models

class CustomPartner(models.Model):
    _inherit = 'res.partner'

    def send_action_email_bid_logistics(self):
        partners = self.env['res.partner'].browse(self._context.get('active_ids', []))
        print(partners)
        template = self.env.ref('fish_market.email_template_logistic')

        for partner in partners:
            if not partner.email:
                raise Exception("Partner '%s' has no email address." % partner.name)
            print(partner.email)
            template.send_mail(partner.id, force_send=True)

    def send_action_email_bid_suppliers(self):
        partners = self.env['res.partner'].browse(self._context.get('active_ids', []))
        print(partners)
        template = self.env.ref('fish_market.email_template_suppliers')

        for partner in partners:
            if not partner.email:
                raise Exception("Partner '%s' has no email address." % partner.name)
            print(partner.email)
            template.send_mail(partner.id, force_send=True)
