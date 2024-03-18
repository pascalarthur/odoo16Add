from odoo import api, models, fields, exceptions
from datetime import datetime
from urllib.parse import urlparse


class CustomerPricelistWizard(models.TransientModel):
    _name = 'customer.price.wizard'
    _description = 'Pricelist Selection Wizard'

    customer_partner_ids = fields.Many2many('res.partner')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True)

    email_body = fields.Html(string='Email Body', readonly=False)

    def compute_email_body(self):
        for record in self:
            email_body = """
            <p>There are new prices available from Afromerge. Please find the details below:</p>
            <table>
                <tr>
                    <th style='border: 1px solid black;'>Product</th>
                    <th style='border: 1px solid black;'>Box Price</th>
                    <th style='border: 1px solid black;'>Available Quantity</th>
                </tr>
            """
            for item in record.pricelist_id.item_ids:
                product_id = item.product_tmpl_id.product_variant_id
                # Get the quantity available in the specified location
                quants = self.env['stock.quant'].search([('product_id', '=', product_id.id),
                                                         ('location_id', '=', record.location_id.id)])
                quantity = sum(quants.mapped('quantity'))
                email_body += f"""
                <tr>
                    <td style='border: 1px solid black;'>{product_id.name}</td>
                    <td style='border: 1px solid black;'>{item.fixed_price}</td>
                    <td style='border: 1px solid black;'>{quantity}</td>
                </tr>
                """
            record.email_body = email_body + "</table>"
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'customer.price.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def confirm_selection(self):
        self.ensure_one()

        if not self.customer_partner_ids:
            raise Exception('No customers selected.')

        my_company_email = self.env.user.company_id.email
        if not my_company_email:
            raise exceptions.UserError(f'Please specify a valid email address for company: {self.env.user.name}.')

        for partner_id in self.customer_partner_ids:
            email_body = f"""
                <p>Dear {partner_id.name},</p>
                {self.email_body}
            """

            # Send email with token link
            template = self.env.ref('fish_market.email_template')
            template.send_mail(
                self.id, email_values={
                    'email_to': partner_id.email,
                    'email_from': my_company_email,
                    'subject': 'Afromerge Customer Info',
                    'body_html': email_body
                }, force_send=True)
