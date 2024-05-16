# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_discount = fields.Monetary(string="Total Discount", compute='_compute_total_discount')

    @api.depends('order_line.discount_amount')
    def _compute_total_discount(self):
        for line in self:
            line.total_discount = sum(line.order_line.mapped('discount_amount'))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    discount_amount = fields.Monetary(string='Discount Amount', store=True, readonly=False)
    _is_changed = fields.Boolean(string='Discount Changed')

    @api.onchange('product_id', 'product_uom_qty', 'price_unit', 'discount')
    def _compute_line_discount(self):
        for line in self:
            if line._is_changed:
                line._is_changed = False
                continue
            if line.product_id and line.discount and line.product_uom_qty and line.price_unit:
                line.discount_amount = ((line.product_uom_qty * line.price_unit) * line.discount) / 100.0
            else:
                line.discount_amount = 0
            line._is_changed = True

    @api.onchange('discount_amount')
    def _compute_line_discount_amount(self):
        for line in self:
            if line._is_changed:
                line._is_changed = False
                continue
            if line.product_id and line.discount_amount and line.product_uom_qty and line.price_unit:
                line.discount = (line.discount_amount / (line.product_uom_qty * line.price_unit)) * 100.0
            else:
                line.discount = 0
            line._is_changed = True
