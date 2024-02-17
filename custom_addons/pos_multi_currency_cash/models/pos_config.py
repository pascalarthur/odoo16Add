from typing import List
from odoo import models, fields, api, _


class PosConfigInherit(models.Model):
    _inherit = "pos.config"

    currency_journal_ids = fields.Many2many('account.journal', string='Currency Journals',
                                            help="Map each currency to a specific journal.")
    location_id = fields.Many2one('stock.location', 'Location', related='picking_type_id.default_location_src_id',
                                  readonly=True)

    available_product_ids = fields.Many2many('product.product', string='Availiable Products',
                                             help="Map each currency to a specific journal.",
                                             compute='_compute_available_product_ids')

    def _compute_available_product_ids(self):
        for res_config in self:
            stocked_products = self.env['stock.quant'].search([('location_id', '=',
                                                                res_config.picking_type_id.default_location_src_id.id),
                                                               ('quantity', '>', 0)])
            res_config.available_product_ids = [(6, 0, stocked_products.mapped('product_id').ids)]


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_journal_ids = fields.Many2many(related='pos_config_id.currency_journal_ids', readonly=False)
    location_id = fields.Many2one(related='pos_config_id.location_id', readonly=False)

    available_product_ids = fields.Many2many(related='pos_config_id.available_product_ids', readonly=False)
