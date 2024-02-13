from odoo import api, models, fields, exceptions
from datetime import datetime
from urllib.parse import urlparse

class ProductOfferWizard(models.TransientModel):
    _name = 'product.offer.wizard'
    _description = 'Product Offer Wizard'

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True)
    email_body = fields.Char(string='Email Body', required=True)
    partner_ids = fields.Many2many('res.partner')
    available_product_pricelist_item_ids = fields.Many2many('product.pricelist.item', string='Available Offers', readonly=False)

    def confirm_selection(self, form_name='product_offer'):
        self.ensure_one()

        if not self.partner_ids:
            raise Exception('No suppliers found.')

        my_company_email = self.env.user.company_id.email
        if not my_company_email:
            raise exceptions.UserError(f'Please specify a valid email address for company: {self.env.user.name}.')

        for partner_id in self.partner_ids:
            token_record = self.env['access.token'].create([{
                'partner_id': partner_id.id,
                'pricelist_id': self.pricelist_id.id,
                'expiry_date': fields.Datetime.add(datetime.now(), days=30),  # 30 day validity
                'product_pricelist_item_ids': self.available_product_pricelist_item_ids.ids,
            }])

            base_url = urlparse(self.env['ir.config_parameter'].sudo().get_param('web.base.url')).hostname
            token_url=f"https://{base_url}/{form_name}/{token_record.token}"

            email_body = f"""
                <p>Hello {partner_id.name},</p>
                <p>{self.email_body}</p>
                <a href="{token_url}">Submit Price</a>
            """

            # Send email with token link
            template = self.env.ref('fish_market.email_template')
            template.with_context(token_url=f"https://{base_url}/{form_name}/{token_record.token}").send_mail(
                self.id,
                email_values={'email_to': partner_id.email, 'email_from': my_company_email, 'subject': 'Afromerge Supplier Info', 'body_html': email_body},
                force_send=True
            )
