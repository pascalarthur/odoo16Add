# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Vishnu KP(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    customer_details = fields.Boolean(String=" Customer Details",
                                      Help="By Enabling the customer details in pos receipt")
    customer_name = fields.Boolean(String=" Customer Name", Help="By Enabling the customer name in pos receipt")
    customer_address = fields.Boolean(String=" Customer Address",
                                      Help="By Enabling the customer Address in pos receipt")
    customer_mobile = fields.Boolean(String=" Customer Mobile", Help="By Enabling the customer mobile in pos receipt")
    customer_phone = fields.Boolean(String=" Customer Phone", Help="By Enabling the customer phone in pos receipt")
    customer_email = fields.Boolean(String=" Customer Email", Help="By Enabling the customer email in pos receipt")
    customer_vat = fields.Boolean(String=" Customer Vat", Help="By Enabling the customer vat details in pos receipt")


class PosConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    customer_details = fields.Boolean(related="pos_config_id.customer_details", readonly=False)
    customer_name = fields.Boolean(related="pos_config_id.customer_name", readonly=False)
    customer_address = fields.Boolean(related="pos_config_id.customer_address", readonly=False)
    customer_mobile = fields.Boolean(related="pos_config_id.customer_mobile", readonly=False)
    customer_phone = fields.Boolean(related="pos_config_id.customer_phone", readonly=False)
    customer_email = fields.Boolean(related="pos_config_id.customer_email", readonly=False)
    customer_vat = fields.Boolean(related="pos_config_id.customer_vat", readonly=False)
