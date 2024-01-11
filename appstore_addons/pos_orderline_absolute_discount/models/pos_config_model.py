from odoo import models, fields, api, _


class PosConfigInherit(models.Model):
    _inherit = "pos.config"

    include_discount_in_prices = fields.Boolean(
        string="Include Discount in Prices",
        help="If box is unchecked the displayed prices will not include discounts",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    include_discount_in_prices = fields.Boolean(related='pos_config_id.include_discount_in_prices', readonly=False)