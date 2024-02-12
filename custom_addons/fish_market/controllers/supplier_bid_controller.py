from collections import defaultdict
from odoo import http, fields
from odoo.http import request


class SupplierBidOrderController(http.Controller):

    def get_token_record(self, token):
        AccessToken = http.request.env['access.token'].sudo()
        return AccessToken.search([('token', '=', token), ('is_used', '=', False)], limit=1)

    def check_token(self, token_record) -> bool:
        return token_record and token_record.expiry_date > fields.Datetime.now()

    @http.route('/supplier_bid/<string:token>', type='http', auth='public')
    def access_form(self, token, **kwargs):
        token_record = self.get_token_record(token)
        if self.check_token(token_record) is True:

            product_templates = http.request.env['product.template'].sudo().search([])
            product_variants = http.request.env['product.product'].sudo().search([])
            attribute_values = http.request.env['product.template.attribute.value'].sudo().search([])

            attribute_values_map = {attr_val.id: attr_val.name for attr_val in attribute_values}
            product_variants_map = {attr_val.id: attr_val.attribute_id.name for attr_val in attribute_values}
            unique_variants_ids = set(product_variants_map.values())
            # Assign variants to product templates -> Create str for variants

            product_temp_vars_dict = defaultdict(dict)

            for product_template_id in product_templates:
                if product_template_id.detailed_type == token_record.detailed_type:
                    product_temp_vars_dict[product_template_id.id]['name'] = product_template_id.name

                    product_temp_vars_dict[product_template_id.id]['product_variants'] = defaultdict(list)
                    product_temp_vars_dict[product_template_id.id]['product_variants_str'] = []
                    product_variants = http.request.env['product.product'].sudo().search([('product_tmpl_id', '=', product_template_id.id)])
                    for product_variant_id in product_variants:
                        if product_variant_id.combination_indices:
                            for key in map(int, product_variant_id.combination_indices.split(',')):
                                product_temp_vars_dict[product_template_id.id]['product_variants'][product_variants_map[key]].append(attribute_values_map[key])
                            product_temp_vars_dict[product_template_id.id]['product_variants_str'].append("; ".join([f'{cat}: {lst[-1]}' for cat, lst in product_temp_vars_dict[product_template_id.id]['product_variants'].items()]))
                    product_temp_vars_dict[product_template_id.id]['product_variants_ids'] = product_variants.ids

            addresses = [f'{token_record.partner_id.street}, {token_record.partner_id.city}, {token_record.partner_id.country_id.name}']

            nad_to_usd_exchange_rate = http.request.env['res.currency'].sudo().search([('name', '=', 'NAD')]).inverse_rate

            return http.request.render('fish_market.supplier_form_template', {
                'supplier': token_record.partner_id,
                'pricelist_id': token_record.pricelist_id,
                'token': token,
                'product_temp_vars_dict': product_temp_vars_dict,
                'nad_to_usd_exchange_rate': nad_to_usd_exchange_rate,
                'addresses': addresses,
                'form_action': '/supplier_bid',
                'form_id': 'supplier_order_form',
            })
        else:
            return "Token is invalid or has expired"

    @http.route('/supplier_bid', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_form(self, **post):
        token = post.get('token')
        token_record = self.get_token_record(token)

        if self.check_token(token_record) is True:
            # Process product details
            product_template_ids = request.httprequest.form.getlist('product_id[]')
            product_ids = request.httprequest.form.getlist('variant_id[]')
            product_quantities = request.httprequest.form.getlist('product_quantity[]')
            price_in_usd = request.httprequest.form.getlist('price_in_usd[]')

            delivery_address = post.get('delivery_address')
            pickup_address = post.get('pickup_address')

            notes = f"Delivery Address: {pickup_address if delivery_address == 'other' else delivery_address}"

            for i in range(len(product_template_ids)):
                product_detail = {
                    'pricelist_id': token_record.pricelist_id.id,
                    'partner_id': token_record.partner_id.id,
                    'product_tmpl_id': int(product_template_ids[i]),
                    'product_id': int(product_ids[i]),
                    'compute_price': 'fixed',
                    'applied_on': '0_product_variant',
                    'fixed_price': float(price_in_usd[i]),
                    'min_quantity': float(product_quantities[i]),
                    'date_start': fields.Datetime.now(),

                    'notes': notes,
                }
                request.env['product.pricelist.item'].sudo().create(product_detail)

            # token_record.is_used = True

            return "Thank you for submitting your prices to Afromerge. The team will come back to you soon!"
        else:
            return "Token is invalid or has expired"