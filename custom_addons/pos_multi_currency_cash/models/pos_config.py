from typing import List
from odoo import models, fields, api, _


class PosConfigInherit(models.Model):
    _inherit = "pos.config"

    currency_journal_ids = fields.Many2many(
        'account.journal',
        string='Currency Journals',
        help="Map each currency to a specific journal."
    )

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_journal_ids = fields.Many2many(related='pos_config_id.currency_journal_ids', readonly=False)
