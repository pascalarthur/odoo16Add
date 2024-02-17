from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    meta_sale_order_id = fields.Many2one('meta.sale.order', string='Meta Sale Order')

    location_id = fields.Many2one('stock.location', string='Origin Location')
    truck_detail_id = fields.Many2one('truck.detail', string='Truck Detail')
    truck_number = fields.Char('Trailer Number')
    horse_number = fields.Char('Horse Number')
    container_number = fields.Char('Container Number')
    seal_number = fields.Char('Seal Number')
    driver_name = fields.Char('Driver Name')
    telephone_number = fields.Char('Telephone Number')

    @api.model
    def check_and_delete_order(self, order_id, creation_date):
        order = self.browse(order_id)
        # Check if the order was not modified (you might need to adjust this logic)
        if order.create_date == fields.Datetime.from_string(creation_date):
            order.unlink()  # Delete the order

    def action_quotation_send_programmatically(self):
        self.ensure_one()
        self.order_line._validate_analytic_distribution()
        mail_template = self._find_mail_template()
        ctx = {
            'model': 'sale.order',
            'res_ids': self.ids,
            'template_id': mail_template.id if mail_template else None,
            'composition_mode': 'comment',
            'email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
        }
        msg = self.env['mail.compose.message'].create(ctx)
        print('action_quotation_send_programmatically 2', mail_template)
        msg.action_send_mail()
        print('action_quotation_send_programmatically 4')

    @api.model
    def _create_invoices(self, grouped=False, final=False):
        # Call the super method to get the invoices created by the original method
        invoices = super(SaleOrder, self)._create_invoices(grouped, final)

        # Iterate over the created invoices
        for invoice in invoices:
            # Set custom fields on each invoice
            invoice.write({
                'truck_number': self.truck_number,
                'horse_number': self.horse_number,
                'container_number': self.container_number,
                'seal_number': self.seal_number,
                'driver_name': self.driver_name,
                'telephone_number': self.telephone_number,
            })

        return invoices
