from odoo import api, models, fields
from odoo.tools.misc import formatLang


class SaleOrder(models.Model):
    _inherit = 'account.move'

    truck_number = fields.Char('Truck Number')
    horse_number = fields.Char('Horse Number')
    container_number = fields.Char('Container Number')
    seal_number = fields.Char('Seal Number')
    driver_name = fields.Char('Driver Name')
    telephone_number = fields.Char('Telephone Number')

    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        super(SaleOrder, self)._compute_tax_totals()
        for record in self:
            print('_compute_alternative_currency_amount_total', record.currency_id, record.company_id.currency_id)
            if record.currency_id.id != record.company_id.currency_id.id:
                self.tax_totals['alternative_currency_amount_total'] = record.amount_total * record.currency_id.rate
                self.tax_totals['alternative_currency_amount_total_formatted'] = formatLang(self.env, self.tax_totals['alternative_currency_amount_total'], currency_obj=record.company_id.currency_id)