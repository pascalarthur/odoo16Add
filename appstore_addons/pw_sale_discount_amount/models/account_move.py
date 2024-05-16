# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    total_discount = fields.Monetary(string="Total Discount", compute='_compute_total_discount')

    @api.depends('invoice_line_ids.discount_amounts')
    def _compute_total_discount(self):
        for line in self:
            line.total_discount = sum(line.invoice_line_ids.mapped('discount_amounts'))

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    discount_amounts = fields.Monetary(string='Discount Amount', compute='_compute_discount_amounts', store=True)

    @api.depends('product_id','quantity','price_unit','discount')
    def _compute_discount_amounts(self):
        for line in self:
            if line.product_id and line.discount and line.quantity and line.price_unit:
                line.discount_amounts = ((line.quantity * line.price_unit) * line.discount) / 100.0
            else:
                line.discount_amounts = 0
