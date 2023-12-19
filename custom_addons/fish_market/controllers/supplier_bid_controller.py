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

            Product = http.request.env['product.template'].sudo()
            products = Product.search([])

            addresses = [f'{token_record.partner_id.street}, {token_record.partner_id.city}, {token_record.partner_id.country_id.name}']

            return http.request.render('fish_market.supplier_form_template', {
                'supplier': token_record.partner_id,
                'pricelist_id': token_record.pricelist_id,
                'token': token,
                'products': list(zip(products.ids, products.mapped('name'))),
                'addresses': addresses,
            })
        else:
            return "Token is invalid or has expired"

    @http.route('/supplier_bid', type='http', auth='public', methods=['POST'], csrf=False)
    def submit_form(self, **post):
        token = post.get('token')
        token_record = self.get_token_record(token)

        currency_usd_id = request.env['res.currency'].sudo().search([('name', '=', 'USD')], limit=1).id

        if self.check_token(token_record) is True:
            # Process product details
            product_ids = request.httprequest.form.getlist('product_id[]')
            product_quantities = request.httprequest.form.getlist('product_quantity[]')
            product_prices = request.httprequest.form.getlist('product_price[]')

            delivery_address = post.get('delivery_address')
            pickup_address = post.get('pickup_address')

            for i in range(len(product_ids)):
                product_detail = {
                    'pricelist_id': token_record.pricelist_id.id,
                    'partner_id': token_record.partner_id.id,
                    'product_tmpl_id': int(product_ids[i]),
                    'compute_price': 'fixed',
                    'applied_on': '1_product',
                    'fixed_price': float(product_prices[i]),
                    'min_quantity': float(product_quantities[i]),
                    'date_start': fields.Datetime.now(),
                }
                request.env['product.pricelist.item'].create(product_detail)

            token_record.is_used = True

            return "Form submitted successfully!"
        else:
            return "Token is invalid or has expired"