######################################################################################
#
#    Hynsys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Hynsys Technologies(<https://www.hynsys.com>).
#    Author: Hynsys Technologies(<https://www.hynsys.com>)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
######################################################################################
# handler for free currency api made by SozinovD in 2023
# main project repo is here https://github.com/fawazahmed0/currency-api

from odoo import models, fields, api
import requests
import datetime
from dateutil.relativedelta import relativedelta


class ResCompany(models.Model):
    _inherit = "res.company"

    currency_interval_period = fields.Selection(
        [
            ("manually", "Manually"),
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ],
        default="manually",
        string="Interval Period",
    )
    curr_next_execution_date = fields.Date(string="Next Execution Date")

    def update_currency_rates(self):
        currency = self.env["res.currency"]
        currency_rate = self.env["res.currency.rate"]
        all_currencies = currency.search([])

        today = fields.Date.today()
        for company in self:
            curr1 = company.currency_id
            for curr2 in all_currencies:
                if curr2.id == curr1.id:
                    continue
                rate = self.get_today_rate(curr1.name, curr2.name)
                if rate == "Not found":
                    continue
                rate = rate * curr1.rate
                already_exists = currency_rate.search(
                    [
                        ("name", "=", today),
                        ("currency_id", "=", curr2.id),
                        ("company_id", "=", company.id),
                    ]
                )
                if already_exists:
                    already_exists.rate = rate
                else:
                    currency_rate.create(
                        {
                            "name": today,
                            "currency_id": curr2.id,
                            "rate": rate,
                            "company_id": company.id,
                        }
                    )
        return True

    @api.model
    def run_update_currency(self):
        records = self.search([("curr_next_execution_date", "<=", fields.Date.today())])
        to_update = self.env["res.company"]
        interval_mapping = {
            "daily": relativedelta(days=+1),
            "weekly": relativedelta(weeks=+1),
            "monthly": relativedelta(months=+1),
        }

        for record in records:
            next_update = interval_mapping.get(record.currency_interval_period)
            if next_update:
                record.curr_next_execution_date = datetime.date.today() + next_update
                to_update |= record
            else:
                record.curr_next_execution_date = False

        if to_update:
            to_update.update_currency_rates()

    def get_rate(self, curr1, curr2, date):
        base_urls_arr = [
            "https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/",
            "https://raw.githubusercontent.com/fawazahmed0/currency-api/1/",
        ]
        suffix_arr = [".min.json", ".json"]
        curr1, curr2 = curr1.lower(), curr2.lower()

        for base_url in base_urls_arr:
            for suff in suffix_arr:
                url = f"{base_url}{date}/currencies/{curr1}/{curr2}{suff}"
                rate = requests.get(url)
                if rate.status_code == 200:
                    return rate.json()[curr2]
        return "Not found"

    def get_today_rate(self, curr1, curr2):
        return self.get_rate(curr1, curr2, "latest")
