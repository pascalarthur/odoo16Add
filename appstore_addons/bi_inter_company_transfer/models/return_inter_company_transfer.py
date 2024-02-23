# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext
import odoo.addons.decimal_precision as dp


class ReturnPickingLine(models.Model):
    _name = "stock.return.picking.inter.company"
    _description = "ReturnPickingLine"


class ReturnInterTransferCompany(models.Model):
    _name = 'return.inter.transfer.company'
    _description = "ReturnInterTransferCompany"
