from odoo import http, fields
from datetime import datetime

class TransportOrderController(http.Controller):

    @http.route('/transport_order/<string:token>', type='http', auth='public')
    def access_form(self, token, **kwargs):
        AccessToken = http.request.env['access.token']
        token_record = AccessToken.search([('token', '=', token), ('is_used', '=', False)], limit=1)

        if token_record and token_record.expiry_date > fields.Datetime.now():
            # Logic to display the form and allow the supplier to fill in details
            # Once the form is submitted, set token_record.is_used to True
            return http.request.render('transport.view_transport_order_form', {'supplier': token_record.partner_id})
        else:
            return "Token is invalid or has expired"
