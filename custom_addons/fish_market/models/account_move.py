from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = 'account.move'

    truck_number = fields.Char('Truck Number')
    horse_number = fields.Char('Horse Number')
    container_number = fields.Char('Container Number')
    seal_number = fields.Char('Seal Number')
    driver_name = fields.Char('Driver Name')
    telephone_number = fields.Char('Telephone Number')

    alternative_currency_amount_total = fields.Monetary('Alternative Total Price', currency_field='currency_id', compute='_compute_alternative_currency_amount_total')

    @api.depends('amount_total', 'currency_id')
    def _compute_alternative_currency_amount_total(self):
        for record in self:
            print('_compute_alternative_currency_amount_total', record.currency_id, record.company_id.currency_id)
            if record.currency_id.id != record.company_id.currency_id.id:
                record.alternative_currency_amount_total = record.amount_total * record.currency_id.rate