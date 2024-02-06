from collections import defaultdict
from odoo import http, fields
from odoo.http import request


class TransportOrderController(http.Controller):

    def get_token_record(self, token):
        AccessToken = http.request.env['access.token'].sudo()
        return AccessToken.search([('token', '=', token), ('is_used', '=', False)], limit=1)

    def check_token(self, token_record) -> bool:
        return token_record and token_record.expiry_date > fields.Datetime.now()

    def get_transport_product_product_ids(self, transport_order_id):

        return transport_product_product_ids

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
        token_record = self.get_token_record(token)

        transport_product_id = token_record.transport_order_id.meta_sale_order_id.transport_product_id
        transport_variants = http.request.env['product.product'].sudo().search([('product_tmpl_id', '=', transport_product_id.id)])

        attribute_values = http.request.env['product.template.attribute.value'].sudo().search([])
        product_variants_map = {attr_val.id: attr_val.name for attr_val in attribute_values}

        transport_product_product_ids = {}
        for product_variant_id in transport_variants:
            if product_variant_id.combination_indices == '':
                return "Please add the following product variants to the transport product: 'One-Way', 'Backload'"
            for key in map(int, product_variant_id.combination_indices.split(',')):
                transport_product_product_ids[product_variants_map[key]] = product_variant_id.id

        if any(key not in transport_product_product_ids.keys() for key in ['One-Way', 'Backload']):
            return "Please add the following product variants to the transport product: 'One-Way', 'Backload'"

        if self.check_token(token_record) is True:
            transport_order = token_record.transport_order_id

            # Process each truck detail
            truck_numbers = request.httprequest.form.getlist('truck_number[]')
            horse_numbers = request.httprequest.form.getlist('horse_number[]')
            container_numbers = request.httprequest.form.getlist('container_number[]')
            driver_names = request.httprequest.form.getlist('driver_name[]')
            telephone_numbers = request.httprequest.form.getlist('telephone_number[]')
            prices_in_usd = request.httprequest.form.getlist('price_in_usd[]')
            max_loads = request.httprequest.form.getlist('max_load_per_truck[]')
            backload_prices = request.httprequest.form.getlist('backload_price[]')

            for ii in range(len(truck_numbers)):
                truck_detail = {
                    'partner_id': token_record.partner_id.id,
                    'transport_order_id': transport_order.id,
                    'meta_sale_order_id': transport_order.meta_sale_order_id.id,
                    'truck_number': truck_numbers[ii],
                    'horse_number': horse_numbers[ii],
                    'container_number': container_numbers[ii],
                    'driver_name': driver_names[ii],
                    'telephone_number': telephone_numbers[ii],

                    'price': float(prices_in_usd[ii]),
                    'max_load': float(max_loads[ii]),
                    'is_backload': False,
                }
                truck_id = request.env['truck.detail'].create(truck_detail)

                product_detail = {
                    'truck_id': truck_id.id,
                    'pricelist_id': int(transport_order.meta_sale_order_id.transport_pricelist_id.id),
                    'partner_id': token_record.partner_id.id,
                    'product_tmpl_id': int(transport_order.meta_sale_order_id.transport_product_id.id),
                    'product_id': transport_product_product_ids['One-Way'],
                    'compute_price': 'fixed',
                    'applied_on': '0_product_variant',
                    'fixed_price': float(prices_in_usd[ii]),

                    'meta_sale_order_id': transport_order.meta_sale_order_id.id,
                }
                product_pricelist_item_id = request.env['product.pricelist.item'].create(product_detail)

                # Every backload item has a corresponding product.pricelist.item
                if backload_prices[ii] != '':
                    truck_detail = {
                        'partner_id': token_record.partner_id.id,
                        'transport_order_id': transport_order.id,
                        'meta_sale_order_id': transport_order.meta_sale_order_id.id,
                        'truck_number': truck_numbers[ii],
                        'horse_number': horse_numbers[ii],
                        'container_number': container_numbers[ii],
                        'driver_name': driver_names[ii],
                        'telephone_number': telephone_numbers[ii],

                        'price': float(backload_prices[ii]),
                        'max_load': float(max_loads[ii]),
                        'is_backload': True,
                    }
                    truck_id = request.env['truck.detail'].create(truck_detail)

                    product_detail = {
                        'truck_id': truck_id.id,
                        'pricelist_id': int(transport_order.meta_sale_order_id.transport_pricelist_id.id),
                        'partner_id': token_record.partner_id.id,
                        'product_tmpl_id': int(transport_order.meta_sale_order_id.transport_product_id.id),
                        'product_id': transport_product_product_ids['Backload'],
                        'compute_price': 'fixed',
                        'applied_on': '0_product_variant',
                        'fixed_price': float(backload_prices[ii]),

                        'meta_sale_order_id': transport_order.meta_sale_order_id.id,
                    }
                    product_pricelist_item_id_backload = request.env['product.pricelist.item'].create(product_detail)

                    product_pricelist_item_id.write({'backload_id': product_pricelist_item_id_backload.id})


            transport_order.write({
                'state': 'received',
            })

            # Optionally, mark the token as used
            # token_record.is_used = True

            return "Form submitted successfully!"
        else:
            return "Token is invalid or has expired"