from odoo import models, fields, api
from datetime import datetime


class RouteDemand(models.Model):
    _name = 'route.demand'
    _description = 'Route Demand'

    route_start_street = fields.Char()
    route_start_street2 = fields.Char()
    route_start_city = fields.Char()
    route_start_zip = fields.Char()
    route_start_state_id = fields.Many2one('res.country.state', string='State')
    route_start_country_id = fields.Many2one('res.country', string='Country')

    route_end_street = fields.Char()
    route_end_street2 = fields.Char()
    route_end_city = fields.Char()
    route_end_zip = fields.Char()
    route_end_state_id = fields.Many2one('res.country.state', string='State')
    route_end_country_id = fields.Many2one('res.country', string='Country')

    container_count = fields.Integer(string='Container Count')
    additional_details = fields.Text(string='Additional Details')

    supplier_ids = fields.Many2many('res.partner')

    def send_email_to_suppliers(self):
        if not self.supplier_ids:
            raise Exception('No suppliers found.')

        my_company_email = self.env.user.company_id.email
        if not my_company_email:
            raise Exception('Invalid or missing email address for the company.')

        for partner in self.supplier_ids:
            # Send the email

            token_record = self.env['access.token'].create([{
                'partner_id': partner.id,
                'expiry_date': fields.Datetime.add(datetime.now(), days=1)  # example for 1 day validity
            }])

            email_body = """
                <p>Hello {partner_name},</p>
                <p>We have a new route demand. Please fill in your price details by following the link below:</p>
                <a href="{token_url}">Submit Price</a>
            """.format(partner_name=partner.name, token_url=f'https://afromergeodoo.site/transport_order/{token_record.token}')

            # Send email with token link
            template = self.env.ref('fish_market.email_template_demand')
            template.with_context(token_url=f'https://afromergeodoo.site/transport_order/{token_record.token}').send_mail(
                self.id,
                email_values={'email_to': partner.email, 'email_from': my_company_email, 'body_html': email_body},
                force_send=True
            )
            # Create a transport.order record for each email sent
            self.env['transport.order'].create({
                'route_start_street': self.route_start_street,
                'route_start_street2': self.route_start_street2,
                'route_start_city': self.route_start_city,
                'route_start_zip': self.route_start_zip,
                'route_start_state_id': self.route_start_state_id.id,
                'route_start_country_id': self.route_start_country_id.id,
                'route_end_street': self.route_end_street,
                'route_end_street2': self.route_end_street2,
                'route_end_city': self.route_end_city,
                'route_end_zip': self.route_end_zip,
                'route_end_state_id': self.route_end_state_id.id,
                'route_end_country_id': self.route_end_country_id.id,
                'container_count': self.container_count,
                'additional_details': self.additional_details,
                'supplier_id': partner.id,
            })
