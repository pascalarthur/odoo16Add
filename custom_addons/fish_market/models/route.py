from odoo import models, fields, api

class RouteDemand(models.Model):
    _name = 'route.demand'
    _description = 'Route Demand'

    route_start = fields.Char('Route Start')
    route_end = fields.Char('Route End')
    container_count = fields.Integer('Container Count')
    additional_details = fields.Text('Additional Details')

    supplier_ids = fields.Many2many('res.partner', string='Suppliers')

    def send_email_to_suppliers(self):
        # Find partners with the "Logistic" tag
        partners = self.env['res.partner'].search([('category_id.name', '=', 'Logistic')])
        if not partners:
            raise Exception('No partners with the "Logistic" tag found.')

        # Prepare email content
        template = self.env.ref('fish_market.email_template_demand')
        for partner in partners:
            template.send_mail(self.id, email_values={'email_to': partner.email}, force_send=True)