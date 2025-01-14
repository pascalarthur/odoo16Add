from odoo import models, fields, api
from datetime import datetime
from urllib.parse import urlparse


class RouteDemand(models.Model):
    _name = 'route.demand'
    _description = 'Route Demand'

    route_start_street = fields.Char()
    route_start_street2 = fields.Char()
    route_start_city = fields.Char()
    route_start_zip = fields.Char()
    route_start_state_id = fields.Many2one('res.country.state')
    route_start_country_id = fields.Many2one('res.country')

    route_end_street = fields.Char()
    route_end_street2 = fields.Char()
    route_end_city = fields.Char()
    route_end_zip = fields.Char()
    route_end_state_id = fields.Many2one('res.country.state')
    route_end_country_id = fields.Many2one('res.country')

    container_demand = fields.Integer(string='Container demand')
    additional_details = fields.Text(string='Additional Details')

    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order')
    partner_ids = fields.Many2many('res.partner')

    def send_email_to_suppliers(self):
        if not self.partner_ids:
            raise Exception('No transporters found.')

        my_company_email = self.env.user.company_id.email
        if not my_company_email:
            raise Exception('Invalid or missing email address for the company.')

        for partner in self.partner_ids:

            token_record = self.env['access.token'].create([{
                'partner_id': partner.id,
                'expiry_date': fields.Datetime.add(datetime.now(), days=1),  # example for 1 day validity
                'route_demand_id': self.id,
            }])

            base_url = urlparse(self.env['ir.config_parameter'].sudo().get_param('web.base.url')).hostname
            email_body = """
                <p>Hello {partner_name},</p>
                <p>We have a new route demand. Please fill in your price details by following the link below:</p>
                <a href="{token_url}">Submit Price</a>
            """.format(partner_name=partner.name, token_url=f"https://{base_url}/route_demand/{token_record.token}")

            # Send email with token link
            template = self.env.ref('fish_market.email_template_demand')
            template.with_context(token_url=f"https://{base_url}/route_demand/{token_record.token}").send_mail(
                self.id, email_values={
                    'email_to': partner.email,
                    'email_from': my_company_email,
                    'body_html': email_body
                }, force_send=True)
