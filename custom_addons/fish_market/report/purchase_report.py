# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Please note that these reports are not multi-currency !!!
#

from odoo import fields, models, api
import matplotlib.pyplot as plt
import base64
from io import BytesIO


class AnalyticsReport(models.Model):
    _name = "fish_market.report.image"
    _description = "Fish Price Report"
    # _auto = False

    def create_image(self):
        # Create a Matplotlib plot
        plt.figure()
        plt.plot([1, 2, 3, 4])
        plt.title("Sample Plot")

        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read())
        buf.close()

        return image_base64

    image_base64 = fields.Binary(string="Image", default=create_image)


class PurchaseReport(models.Model):
    _name = "fish_market.report"
    _description = "Purchase Report"
    _auto = False
    # _order = 'date_order desc, price_total desc'

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
    date = fields.Date('Date', readonly=True)
    write_date = fields.Date('Write Date', readonly=True)
    location_id = fields.Char('Location', readonly=True)


    def init(self):
        return self._cr.execute("""
            CREATE OR REPLACE VIEW fish_market_report AS (
                SELECT
                    row_number() over() as id,
                    sub.date,
                    sub.date as write_date,
                    sub.price,
                    sub.size,
                    sub.product_id,
                    sub.location_id
                FROM (
                    SELECT
                        pc.date as date,
                        pc.price as price,
                        pc.size as size,
                        pc.product_id as product_id,
                        'Walvis' as location_id
                    FROM
                        walvis_bay_price_collection_model pc
                    UNION ALL
                    SELECT
                        zc.date as date,
                        zc.price as price,
                        zc.size as size,
                        zc.product_id as product_id,
                        'Zambia' as location_id
                    FROM
                        zambia_price_collection_model zc
                ) sub
            )
        """)
