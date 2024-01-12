# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from itertools import groupby
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext
import odoo.addons.decimal_precision as dp

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    
    validate_picking = fields.Boolean('Validate Receipt/picking in so/po ' , default = False,related="company_id.validate_picking",readonly=False)
    create_invoice = fields.Boolean('Create Invoice/Bill in so/po ' , default = False,related="company_id.create_invoice",readonly=False)
    validate_invoice = fields.Boolean('Validate Invoice/Bill in so/po ' , default = False,related="company_id.validate_invoice",readonly=False)
    allow_auto_intercompany = fields.Boolean('Allow Auto Intercompany Transaction' , default = False,related="company_id.allow_auto_intercompany",readonly=False)


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        
        res.update(validate_picking = self.env['ir.config_parameter'].sudo().get_param('bi_inter_company_transfer.validate_picking'))
        res.update(create_invoice = self.env['ir.config_parameter'].sudo().get_param('bi_inter_company_transfer.create_invoice'))
        res.update(validate_invoice = self.env['ir.config_parameter'].sudo().get_param('bi_inter_company_transfer.validate_invoice'))
        res.update(allow_auto_intercompany = self.env['ir.config_parameter'].sudo().get_param('bi_inter_company_transfer.allow_auto_intercompany'))
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        
        self.env['ir.config_parameter'].sudo().set_param('bi_inter_company_transfer.validate_picking', self.validate_picking)
        self.env['ir.config_parameter'].sudo().set_param('bi_inter_company_transfer.create_invoice', self.create_invoice)
        self.env['ir.config_parameter'].sudo().set_param('bi_inter_company_transfer.validate_invoice', self.validate_invoice)
        self.env['ir.config_parameter'].sudo().set_param('bi_inter_company_transfer.allow_auto_intercompany', self.allow_auto_intercompany)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: