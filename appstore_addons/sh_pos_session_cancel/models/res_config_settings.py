# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    sh_pos_operation_type = fields.Selection([('cancel_delete', 'Cancel and Delete'), ('cancel', 'Cancel')],
                                          string="Opration Type",default='cancel_delete')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_pos_operation_type = fields.Selection(
        string="Opration Type", related="company_id.sh_pos_operation_type", readonly=False)
