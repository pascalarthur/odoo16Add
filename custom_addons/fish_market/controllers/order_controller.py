from odoo import http, fields
from odoo.http import request


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
            nad_to_usd_exchange_rate = http.request.env['res.currency'].sudo().search([('name', '=', 'NAD')]).inverse_rate

            # Pass transport order data to the template
            return http.request.render('fish_market.logistic_form_template', {
                'supplier': token_record.partner_id,
                'transport_order': transport_order,
                'nad_to_usd_exchange_rate': nad_to_usd_exchange_rate,
                'token': token,
            })
        else:
            return "Token is invalid or has expired"

    @http.route('/submit_form', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_form(self, **post):
        token = post.get('token')

        exchange_rate = float(post.get('nad_to_usd_exchange_rate'))

        token_record = self.get_token_record(token)
        if self.check_token(token_record) is True:
            transport_order = token_record.transport_order_id

            # Process each truck detail
            truck_numbers = request.httprequest.form.getlist('truck_number[]')
            horse_numbers = request.httprequest.form.getlist('horse_number[]')
            container_numbers = request.httprequest.form.getlist('container_number[]')
            driver_names = request.httprequest.form.getlist('driver_name[]')
            telephone_numbers = request.httprequest.form.getlist('telephone_number[]')
            price_per_truck = request.httprequest.form.getlist('price_per_truck[]')
            max_loads = request.httprequest.form.getlist('max_load_per_truck[]')

            print('submit_form', exchange_rate, price_per_truck)

            for ii in range(len(truck_numbers)):
                truck_detail = {
                    'truck_number': truck_numbers[ii],
                    'horse_number': horse_numbers[ii],
                    'container_number': container_numbers[ii],
                    'driver_name': driver_names[ii],
                    'telephone_number': telephone_numbers[ii],
                    'price': float(price_per_truck[ii]) * exchange_rate if price_per_truck[ii] else 0.0,
                    'max_load': float(max_loads[ii]),
                    'transport_order_id': transport_order.id,
                    'partner_id': transport_order.partner_id.id,
                    'meta_sale_order_id': transport_order.meta_sale_order_id.id,
                }
                request.env['truck.detail'].create(truck_detail)

            transport_order.write({
                'state': 'received',
                # Handle the overall price if needed
            })

            # Optionally, mark the token as used
            token_record.is_used = True

            return "Form submitted successfully!"
        else:
            return "Token is invalid or has expired"