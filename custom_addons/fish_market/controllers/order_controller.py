from odoo import http, fields
from datetime import datetime

class TransportOrderController(http.Controller):

    def get_token_record(self, token):
        AccessToken = http.request.env['access.token'].sudo()
        return AccessToken.search([('token', '=', token), ('is_used', '=', False)], limit=1)

    def check_token(self, token_record) -> bool:
        return token_record and token_record.expiry_date > fields.Datetime.now()

    @http.route('/transport_order/<string:token>', type='http', auth='public')
    def access_form(self, token, **kwargs):
        token_record = self.get_token_record(token)
        if self.check_token(token_record) is True:
            transport_order = token_record.transport_order_id

            # Pass transport order data to the template
            return http.request.render('transport.public_form_template', {
                'supplier': token_record.partner_id,
                'transport_order': transport_order,
                'token': token,
            })
        else:
            return "Token is invalid or has expired"

    @http.route('/submit_form', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_form(self, **post):
        token = post.get('token')
        price = post.get('price')

        print(price)

        token_record = self.get_token_record(token)
        if self.check_token(token_record) is True:
            transport_order = token_record.transport_order_id

            transport_order.write({
                'state': 'received',
                'price': float(price) if price else 0.0
            })

            # Optionally, mark the token as used
            token_record.is_used = True

            return "Form submitted successfully!"
        else:
            return "Token is invalid or has expired"
