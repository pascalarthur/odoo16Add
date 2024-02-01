from collections import defaultdict
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

            transport_product_id = transport_order.meta_sale_order_id.transport_product_id
            transport_variants = http.request.env['product.product'].sudo().search([('product_tmpl_id', '=', transport_product_id.id)])

            attribute_values = http.request.env['product.template.attribute.value'].sudo().search([])
            product_variants_map = {attr_val.id: attr_val.name for attr_val in attribute_values}

            transport_product_product_ids = {}
            for product_variant_id in transport_variants:
                for key in map(int, product_variant_id.combination_indices.split(',')):
                    transport_product_product_ids[product_variants_map[key]] = product_variant_id.id

            # Pass transport order data to the template
            return http.request.render('fish_market.logistic_form_template', {
                'supplier': token_record.partner_id,
                'transport_order': transport_order,
                'nad_to_usd_exchange_rate': nad_to_usd_exchange_rate,
                'transport_product_product_ids': transport_product_product_ids,
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
            product_prodcut_ids = request.httprequest.form.getlist('product_prodcut_ids[]')
            backload_ids = request.httprequest.form.getlist('backload_ids[]')
            item_ids = request.httprequest.form.getlist('item_ids[]')

            product_pricelist_item_ids = []

            for ii in range(len(truck_numbers)):
                price = float(price_per_truck[ii]) / exchange_rate if price_per_truck[ii] else 0.0

                truck_detail = {
                    'partner_id': token_record.partner_id.id,
                    'transport_order_id': transport_order.id,
                    'meta_sale_order_id': transport_order.meta_sale_order_id.id,
                    'truck_number': truck_numbers[ii],
                    'horse_number': horse_numbers[ii],
                    'container_number': container_numbers[ii],
                    'driver_name': driver_names[ii],
                    'telephone_number': telephone_numbers[ii],

                    'price': price,
                    'max_load': float(max_loads[ii]),
                }

                truck_id = request.env['truck.detail'].create(truck_detail)

                product_detail = {
                    'truck_id': truck_id.id,
                    'pricelist_id': int(transport_order.meta_sale_order_id.transport_pricelist_id.id),
                    'partner_id': token_record.partner_id.id,
                    'product_tmpl_id': int(transport_order.meta_sale_order_id.transport_product_id.id),
                    'product_id': int(product_prodcut_ids[ii]),
                    'compute_price': 'fixed',
                    'applied_on': '0_product_variant',
                    'fixed_price': price,

                    'meta_sale_order_id': transport_order.meta_sale_order_id.id,
                }

                product_pricelist_item_id = request.env['product.pricelist.item'].create(product_detail)

                # Every backload item has a corresponding product.pricelist.item
                if backload_ids[ii] != '-1':
                    product_pricelist_item_ids[item_ids.index(backload_ids[ii])].write({'backload_id': product_pricelist_item_id.id})

                product_pricelist_item_ids.append(product_pricelist_item_id)

            transport_order.write({
                'state': 'received',
            })

            # Optionally, mark the token as used
            # token_record.is_used = True

            return "Form submitted successfully!"
        else:
            return "Token is invalid or has expired"