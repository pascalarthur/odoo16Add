from odoo import fields, models, api
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import base64
from io import BytesIO
import pytz
from datetime import datetime
import pandas as pd


class AnalyticsReport(models.Model):
    _name = "fish_market.report.image"
    _description = "Fish Price Report"
    _auto = False

    def fetch_data(self):
        # Fetch data from fish_market.report
        reports = self.env['fish_market.report'].search([])
        dates = reports.mapped('date')
        prices = reports.mapped('price')
        location_ids = reports.mapped('location_id')
        return dates, prices, location_ids

    def create_image(self):
        # Fetch data
        dates, prices, location_ids = self.fetch_data()
        df = pd.DataFrame({'Date': pd.to_datetime(dates), 'Price': prices, 'Location': location_ids})

        fig, (ax_1) = plt.subplots(nrows=1, ncols=1)
        sns.lineplot(data=df, x='Date', y='Price', hue='Location', ax=ax_1)

        ax_1.set_xticks(df['Date'])
        ax_1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y'))
        ax_1.set_xticklabels(ax_1.get_xticklabels(), rotation=45, ha="right", rotation_mode='anchor')

        buf = BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format='png', dpi=300)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read())
        buf.close()

        return image_base64

    image_base64 = fields.Image(string="Report", default=create_image, readonly=True, _log_access = True)

    namibia_tz = pytz.timezone('Africa/Windhoek')
    write_date = fields.Char(default=datetime.now(namibia_tz).strftime("%d/%m/%Y"), string='Report - Date', readonly=True)


class PurchaseReport(models.Model):
    _name = "fish_market.report"
    _description = "Purchase Report"
    _auto = False
    # _order = 'date_order desc, price_total desc'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    # partner_id = fields.Many2one('res.partner', 'Vendor', readonly=True)
    # product_uom = fields.Many2one('uom.uom', 'Reference Unit of Measure', required=True)
    # company_id = fields.Many2one('res.company', 'Company', readonly=True)
    # currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    # product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)

    # reference = fields.Char('Reference', readonly=True)

    size = fields.Float('Fish Size', readonly=True)
    # quantity = fields.Float('Number of Tons', readonly=True)
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
