from odoo import models, fields, exceptions
from datetime import datetime
from urllib.parse import urlparse

class PricelistWizard(models.TransientModel):
    _name = 'supplier.price.wizard'
    _description = 'Pricelist Selection Wizard'

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True)

    email_body = fields.Char(string='Email Body', required=True, default='Do you have new prices or products. Please fill in your price details by following the link below:')

    detailed_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product'),
        ('transport', 'Transport')], string='Product Type', default='product', required=True)

    def confirm_selection(self):
        self.ensure_one()

        logistic_partner_ids = self.env['res.partner'].search([('category_id.name', '=', 'Supplier')])

        if not logistic_partner_ids:
            raise Exception('No suppliers found.')

        my_company_email = self.env.user.company_id.email
        if not my_company_email:
            raise exceptions.UserError(f'Please specify a valid email address for company: {self.env.user.name}.')

        for partner_id in logistic_partner_ids:
            token_record = self.env['access.token'].create([{
                'partner_id': partner_id.id,
                'pricelist_id': self.pricelist_id.id,
                'expiry_date': fields.Datetime.add(datetime.now(), days=1),  # example for 1 day validity
                'detailed_type': self.detailed_type,
            }])

            base_url = urlparse(self.env['ir.config_parameter'].sudo().get_param('web.base.url')).hostname
            token_url=f"https://{base_url}/supplier_bid/{token_record.token}"

            email_body = f"""
                <p>Hello {partner_id.name},</p>
                <p>{self.email_body}</p>
                <a href="{token_url}">Submit Price</a>
            """

            # Send email with token link
            template = self.env.ref('fish_market.email_template')
            template.with_context(token_url=f"https://{base_url}/supplier_bid/{token_record.token}").send_mail(
                self.id,
                email_values={'email_to': partner_id.email, 'email_from': my_company_email, 'subject': 'Afromerge Supplier Info', 'body_html': email_body},
                force_send=True
            )
