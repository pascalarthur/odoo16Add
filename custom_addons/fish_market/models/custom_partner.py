from odoo import fields, models

class CustomPartner(models.Model):
    _inherit = 'res.partner'

    # Add custom fields here
    membership_state = fields.Char(string='Custom Field')

    def send_action_email_bid(self):
        partners = self.env['res.partner'].browse(self._context.get('active_ids', []))
        print(partners)
        template = self.env.ref('fish_market.email_template_hello_world')

        for partner in partners:
            if not partner.email:
                raise Exception("Partner '%s' has no email address." % partner.name)
            print(partner.email)
            template.send_mail(partner.id, force_send=True)