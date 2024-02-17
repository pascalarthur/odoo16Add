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
            nad_to_usd_exchange_rate = http.request.env['res.currency'].sudo().search([('name', '=', 'NAD')]).inverse_rate

            product_pricelist_items = http.request.env['product.pricelist.item'].sudo().search_read(
                [('id', 'in', token_record.product_pricelist_item_ids.ids)],
                ['product_tmpl_id', 'product_id', 'fixed_price', 'date_start', 'truck_id']
            )
            for product_pricelist_item in product_pricelist_items:
                if product_pricelist_item['date_start']:
                    product_pricelist_item['date_start'] = product_pricelist_item['date_start'].strftime('%Y-%m-%d')

            obj_start_end_dict = http.request.env['truck.detail'].sudo().search_read(
                [('id', '=', product_pricelist_items[0]['truck_id'][0])],
                ['route_start_street', 'route_start_street2', 'route_start_city', 'route_start_zip', 'route_start_state_id', 'route_start_country_id',
                 'route_end_street', 'route_end_street2', 'route_end_city', 'route_end_zip', 'route_end_state_id', 'route_end_country_id']
            )[0]
            # route_start_state_id, ... are tuples of type (id, name)
            for key, value in obj_start_end_dict.items():
                if type(value) is tuple:
                    obj_start_end_dict[key] = obj_start_end_dict[key][1]

            return http.request.render('fish_market.supplier_form_template', {
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

    @http.route('/product_offer', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_form(self, **post):
        token = post.get('token')
        token_record = self.get_token_record(token)

        if self.check_token(token_record) is True:
            # Process product details
            product_pricelist_item_ids = request.httprequest.form.getlist('product_pricelist_item_id[]')
            prices_in_usd = request.httprequest.form.getlist('price_in_usd[]')

            product_pricelist_item_ids = http.request.env['product.pricelist.item'].sudo().search(
                [('id', 'in', token_record.product_pricelist_item_ids.ids)],
            )

            for i, product_pricelist_item_id in enumerate(product_pricelist_item_ids):
                if prices_in_usd[i] != '':
                    product_detail = {
                        'pricelist_id': token_record.pricelist_id.id,
                        'partner_id': token_record.partner_id.id,
                        'product_tmpl_id': product_pricelist_item_id.product_tmpl_id.id,
                        'product_id': product_pricelist_item_id.product_id.id,
                        'compute_price': 'fixed',
                        'applied_on': '0_product_variant',
                        'fixed_price': float(prices_in_usd[i]),
                        'date_start': fields.Datetime.now(),
                    }
                    request.env['product.pricelist.item'].sudo().create(product_detail)

            # token_record.is_used = True

            return "Thank you for submitting your prices to Afromerge. The team will come back to you soon!"
        else:
            return "Token is invalid or has expired"