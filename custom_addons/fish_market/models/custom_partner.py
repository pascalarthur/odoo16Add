from datetime import datetime
from odoo import fields, models

class CustomPartner(models.Model):
    _inherit = 'res.partner'

    def send_action_email_bid_suppliers(self):
        logistic_partner_ids = self.env['res.partner'].search([('category_id.name', '=', 'Supplier')])

        if not logistic_partner_ids:
            raise Exception('No suppliers found.')

        my_company_email = self.env.user.company_id.email
        if not my_company_email:
            raise Exception('Invalid or missing email address for the company.')

        for partner_id in logistic_partner_ids:
            token_record = self.env['access.token'].create([{
                'partner_id': partner_id.id,
                'expiry_date': fields.Datetime.add(datetime.now(), days=1),  # example for 1 day validity
            }])

            email_body = """
                <p>Hello {partner_name},</p>
                <p>We have a new route demand. Please fill in your price details by following the link below:</p>
                <a href="{token_url}">Submit Price</a>
            """.format(partner_name=partner_id.name, token_url=f'https://afromergeodoo.site/supplier_bid/{token_record.token}')

            # Send email with token link
            template = self.env.ref('fish_market.email_template')
            template.with_context(token_url=f'https://afromergeodoo.site/supplier_bid/{token_record.token}').send_mail(
                self.id,
                email_values={'email_to': partner_id.email, 'email_from': my_company_email, 'subject': 'Afromerge Supplier Info', 'body_html': email_body},
                force_send=True
            )

    def send_action_email_bid_logistics(self):
        partners = self.env['res.partner'].browse(self._context.get('active_ids', []))
        template = self.env.ref('fish_market.email_template_logistic')

        for partner in partners:
            if not partner.email:
                raise Exception("Partner '%s' has no email address." % partner.name)
            template.send_mail(partner.id, force_send=True)


