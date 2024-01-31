from odoo import api, models, fields
from odoo.tools.misc import formatLang


class SaleOrder(models.Model):
    _inherit = 'account.move'

    truck_number = fields.Char('Trailer Number')
    horse_number = fields.Char('Horse Number')
    container_number = fields.Char('Container Number')
    seal_number = fields.Char('Seal Number')
    driver_name = fields.Char('Driver Name')
    telephone_number = fields.Char('Telephone Number')