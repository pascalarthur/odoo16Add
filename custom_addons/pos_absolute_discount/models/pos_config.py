from odoo import models, fields, api, _


class PosConfigInherit(models.Model):
    _inherit = "pos.config"

    use_absolute_discount = fields.Boolean(
        string="Use absolute Discount",
        help="If box is unchecked the displayed prices will not include discounts",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_absolute_discount = fields.Boolean(related='pos_config_id.use_absolute_discount', readonly=False)
