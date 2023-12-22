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
from odoo import models, fields, api
import datetime
from dateutil.relativedelta import relativedelta


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_hy_currency_rate = fields.Boolean(string="Automatic Currency Rates")
    currency_interval_period = fields.Selection(
        related="company_id.currency_interval_period", readonly=False
    )
    curr_next_execution_date = fields.Date(
        related="company_id.curr_next_execution_date", readonly=False
    )

    @api.onchange("currency_interval_period")
    def onchange_currency_interval_period(self):
        if self.company_id.curr_next_execution_date:
            return

        interval_mapping = {
            "daily": relativedelta(days=+1),
            "weekly": relativedelta(weeks=+1),
            "monthly": relativedelta(months=+1),
        }

        next_update = interval_mapping.get(self.currency_interval_period)
        if next_update:
            self.curr_next_execution_date = datetime.date.today() + next_update
        else:
            self.curr_next_execution_date = False

    def update_currency_rate(self):
        self.ensure_one()
        self.company_id.update_currency_rates()
