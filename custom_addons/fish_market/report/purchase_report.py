# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Please note that these reports are not multi-currency !!!
#

from odoo import fields, models, api


class PurchaseReport(models.Model):
    _name = "fish_market.report"
    _description = "Purchase Report"
    _auto = False
    _order = 'date_order desc, price_total desc'

    state = fields.Selection([
        ('draft', 'Draft RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], 'Status', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Vendor', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Reference Unit of Measure', required=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)

    reference = fields.Char('Reference', readonly=True)

    size = fields.Float('Fish Size', readonly=True)
    quantity = fields.Float('Number of Tons', readonly=True)
    price = fields.Float('Price', readonly=True)

    @property
    def _table_query(self):
        ''' Report needs to be dynamic to take into account multi-company selected + multi-currency rates '''
        return '%s %s %s %s' % (self._select(), self._from(), self._where(), self._group_by())

    def _select(self):
        select_str = """
            SELECT
                min(pc.id) as id,
                pc.partner_id,
                pc.product_id,
                pc.currency_id,
                pc.size,
                pc.quantity,
                pc.price
            """
        return select_str

    def _from(self):
        from_str = """
            FROM
                walvis_bay_price_collection_model pc
                LEFT JOIN res_partner partner ON pc.partner_id = partner.id
                LEFT JOIN product_product p ON pc.product_id = p.id
                LEFT JOIN product_template t ON p.product_tmpl_id = t.id
                LEFT JOIN uom_uom uom ON t.uom_id = uom.id
                LEFT JOIN res_currency cur ON pc.currency_id = cur.id
        """
        return from_str

    def _where(self):
        return """
            WHERE
                pc.id IS NOT NULL
        """

    def _group_by(self):
        group_by_str = """
            GROUP BY
                pc.partner_id,
                pc.product_id,
                pc.currency_id,
                pc.size,
                pc.quantity,
                pc.price

        """
        return group_by_str

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """
        This is a hack to allow us to correctly calculate the average price of product.
        """
        if 'price_average:avg' in fields:
            fields.extend(['aggregated_qty_ordered:array_agg(qty_ordered)'])
            fields.extend(['aggregated_price_average:array_agg(price_average)'])

        res = []
        if fields:
            res = super(PurchaseReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if 'price_average:avg' in fields:
            qties = 'aggregated_qty_ordered'
            special_field = 'aggregated_price_average'
            for data in res:
                if data[special_field] and data[qties]:
                    total_unit_cost = sum(float(value) * float(qty) for value, qty in zip(data[special_field], data[qties]) if qty and value)
                    total_qty_ordered = sum(float(qty) for qty in data[qties] if qty)
                    data['price_average'] = (total_unit_cost / total_qty_ordered) if total_qty_ordered else 0
                del data[special_field]
                del data[qties]

        return res
