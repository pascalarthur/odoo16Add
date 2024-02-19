from collections import defaultdict
from odoo import http, fields
from odoo.http import request


class ProductOfferController(http.Controller):
    def get_token_record(self, token):
        AccessToken = http.request.env['access.token'].sudo()
        return AccessToken.search([('token', '=', token), ('is_used', '=', False)], limit=1)

    def check_token(self, token_record) -> bool:
        return token_record and token_record.expiry_date > fields.Datetime.now()

    @http.route('/product_offer/<string:token>', type='http', auth='public')
    def access_form(self, token, **kwargs):
        token_record = self.get_token_record(token)
        if self.check_token(token_record) is True:
            nad_to_usd_exchange_rate = http.request.env['res.currency'].sudo().search([('name', '=', 'NAD')
                                                                                       ]).inverse_rate

            product_pricelist_items = http.request.env['product.pricelist.item'].sudo().search_read(
                [('id', 'in', token_record.product_pricelist_item_ids.ids)],
                ['product_tmpl_id', 'product_id', 'fixed_price', 'date_start', 'date_end', 'truck_route_id'])
            for product_pricelist_item in product_pricelist_items:
                if product_pricelist_item['date_start']:
                    product_pricelist_item['date_start'] = product_pricelist_item['date_start'].strftime('%d-%m-%Y')
                if product_pricelist_item['date_end']:
                    product_pricelist_item['date_end'] = product_pricelist_item['date_end'].strftime('%d-%m-%Y')
                # add max load to product_pricelist_item
                product_pricelist_item['max_load'] = http.request.env['truck.route'].sudo().search(
                    [('id', '=', product_pricelist_item['truck_route_id'][0])]).max_load

            obj_start_end_dict = http.request.env['truck.route'].sudo().search_read(
                [('id', '=', product_pricelist_items[0]['truck_route_id'][0])], [
                    'route_start_street', 'route_start_street2', 'route_start_city', 'route_start_zip',
                    'route_start_state_id', 'route_start_country_id', 'route_end_street', 'route_end_street2',
                    'route_end_city', 'route_end_zip', 'route_end_state_id', 'route_end_country_id'
                ])[0]
            # route_start_state_id, ... are tuples of type (id, name)
            for key, value in obj_start_end_dict.items():
                if type(value) is tuple:
                    obj_start_end_dict[key] = obj_start_end_dict[key][1]

            return http.request.render(
                'fish_market.supplier_form_template', {
                    'token': token,
                    'supplier': token_record.partner_id,
                    'pricelist_id': token_record.pricelist_id,
                    'product_pricelist_items': product_pricelist_items,
                    'obj_start_end': obj_start_end_dict,
                    'nad_to_usd_exchange_rate': nad_to_usd_exchange_rate,
                    'form_action': '/product_offer',
                    'form_id': 'product_offer_form',
                })
        else:
            return "Token is invalid or has expired"

    def create_truck_and_pricelist_item(self, token_record, product_pricelist_item_id: list, price_in_usd: float,
                                        approx_loading_time: float, approx_offloading_time: float) -> None:
        truck_routes = {
            'truck_id': product_pricelist_item_id.truck_route_id.truck_id.id,
            'partner_id': token_record.partner_id.id,
            'container_number': product_pricelist_item_id.truck_route_id.container_number,
            'driver_name': product_pricelist_item_id.truck_route_id.driver_name,
            'telephone_number': product_pricelist_item_id.truck_route_id.telephone_number,
            'route_start_street': product_pricelist_item_id.truck_route_id.route_end_street,
            'route_start_street2': product_pricelist_item_id.truck_route_id.route_end_street2,
            'route_start_city': product_pricelist_item_id.truck_route_id.route_end_city,
            'route_start_zip': product_pricelist_item_id.truck_route_id.route_end_zip,
            'route_start_state_id': product_pricelist_item_id.truck_route_id.route_end_state_id.id,
            'route_start_country_id': product_pricelist_item_id.truck_route_id.route_end_country_id.id,
            'route_end_street': product_pricelist_item_id.truck_route_id.route_start_street,
            'route_end_street2': product_pricelist_item_id.truck_route_id.route_start_street2,
            'route_end_city': product_pricelist_item_id.truck_route_id.route_start_city,
            'route_end_zip': product_pricelist_item_id.truck_route_id.route_start_zip,
            'route_end_state_id': product_pricelist_item_id.truck_route_id.route_start_state_id.id,
            'route_end_country_id': product_pricelist_item_id.truck_route_id.route_start_country_id.id,
            'price': price_in_usd,
            'max_load': product_pricelist_item_id.truck_route_id.max_load,
            'is_backload': True,
            'date_start': product_pricelist_item_id.date_start,
            'date_end': product_pricelist_item_id.date_end,
            'approx_loading_time': approx_loading_time,
            'approx_offloading_time': approx_offloading_time,
        }
        truck_route_id = request.env['truck.route'].sudo().create(truck_routes)

        product_pricelist_item_details = {
            'truck_route_id': truck_route_id.id,
            'pricelist_id': token_record.pricelist_id.id,
            'partner_id': token_record.partner_id.id,
            'product_tmpl_id': product_pricelist_item_id.product_tmpl_id.id,
            'product_id': product_pricelist_item_id.product_id.id,
            'compute_price': 'fixed',
            'applied_on': '0_product_variant',
            'fixed_price': price_in_usd,
            'date_start': product_pricelist_item_id.date_start,
            'date_end': product_pricelist_item_id.date_end,
        }
        request.env['product.pricelist.item'].sudo().create(product_pricelist_item_details)

    @http.route('/product_offer', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_form(self, **post):
        token = post.get('token')
        token_record = self.get_token_record(token)

        if self.check_token(token_record) is True:
            # Process product details
            product_pricelist_item_ids = request.httprequest.form.getlist('product_pricelist_item_id[]')
            prices_in_usd = request.httprequest.form.getlist('price_in_usd[]')
            approx_loading_times = request.httprequest.form.getlist('approx_loading_time[]')
            approx_offloading_times = request.httprequest.form.getlist('approx_offloading_time[]')

            product_pricelist_item_ids = http.request.env['product.pricelist.item'].sudo().search([
                ('id', 'in', token_record.product_pricelist_item_ids.ids)
            ])

            for ii, product_pricelist_item_id in enumerate(product_pricelist_item_ids):
                if prices_in_usd[ii] != '':
                    self.create_truck_and_pricelist_item(token_record, product_pricelist_item_id,
                                                         float(prices_in_usd[ii]), float(approx_loading_times[ii]),
                                                         float(approx_offloading_times[ii]))
            # token_record.is_used = True

            return "Thank you for submitting your prices to Afromerge. The team will come back to you soon!"
        else:
            return "Token is invalid or has expired"
