from typing import List
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_inter_company_transactions = fields.Boolean("Enable Inter-Company Transactions")


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

