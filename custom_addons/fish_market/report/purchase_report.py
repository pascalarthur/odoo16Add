from odoo import fields, models, api
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import base64
from io import BytesIO
import pytz
from datetime import datetime
import pandas as pd


class AnalyticsReport(models.TransientModel):
    _name = "fish_market.report.image"
    _description = "Fish Price Report"

    def fetch_data(self):
        # Fetch data from fish_market.report
        dates, prices, location_ids = [], [], []
        pricelist_items_wvb_id = self.env['product.pricelist.item'].search([
            ('pricelist_id.name', 'in', ["WvB USD pricelist", "Zambia USD Pricelist"])
        ])
        for record in pricelist_items_wvb_id:
            dates.extend([date.strftime('%Y-%m-%d') for date in record.mapped('create_date')])
            prices.extend(record.mapped('fixed_price'))
            location_ids.extend(record.mapped('pricelist_id.name'))
        return dates, prices, location_ids

    def create_image(self):
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

    image_base64 = fields.Image(string="Report", default=create_image, readonly=True)

    namibia_tz = pytz.timezone('Africa/Windhoek')
    write_date = fields.Char(default=datetime.now(namibia_tz).strftime("%d/%m/%Y"), string='Report - Date',
                             readonly=True)
