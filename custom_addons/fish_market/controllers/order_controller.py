from odoo import http, fields
from odoo.http import request
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
            return http.request.render('fish_market.public_form_template', {
                'supplier': token_record.partner_id,
                'transport_order': transport_order,
                'token': token,
            })
        else:
            return "Token is invalid or has expired"

    @http.route('/submit_form', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_form(self, **post):
        token = post.get('token')

        token_record = self.get_token_record(token)
        if self.check_token(token_record) is True:
            transport_order = token_record.transport_order_id

            # Process each truck detail
            truck_numbers = request.httprequest.form.getlist('truck_number[]')
            driver_names = request.httprequest.form.getlist('driver_name[]')
            telephone_numbers = request.httprequest.form.getlist('telephone_number[]')
            prices_per_truck = request.httprequest.form.getlist('price_per_truck[]')

            truck_details_data = []
            for ii in range(len(truck_numbers)):
                truck_detail = {
                    'truck_number': truck_numbers[ii],
                    'driver_name': driver_names[ii],
                    'telephone_number': telephone_numbers[ii],
                    'price': float(prices_per_truck[ii]) if prices_per_truck[ii] else 0.0,
                    'transport_order_id': transport_order.id
                }
                truck_details_data.append(truck_detail)

            # Create or update truck details
            for truck_detail in truck_details_data:
                request.env['truck.detail'].create(truck_detail)

            transport_order.write({
                'state': 'received',
                # Handle the overall price if needed
            })

            # Optionally, mark the token as used
            # token_record.is_used = True

            return "Form submitted successfully!"
        else:
            return "Token is invalid or has expired"