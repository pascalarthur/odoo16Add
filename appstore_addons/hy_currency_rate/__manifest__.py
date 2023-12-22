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
{
    "name": "Automatic Currency Rate",
    "version": "17.0.1.0.0",
    "description": "Sync Currency Rates Automatically",
    "summary": """
    This module syncs the currency rate of enabled currencies in the database
    automatically. This feature is something similar to what is available in Odoo
    Enterprise, but uses `https://github.com/fawazahmed0/currency-api` to get the
    currency rates.
    """,
    "author": "Hynsys Technologies",
    "website": "https://www.hynsys.com",
    "support": "info@hynsys.com",
    "license": "LGPL-3",
    "category": "Accounting",
    "images": ["static/description/images/automatic_currency_rate.png"],
    "depends": ["account"],
    "data": [
        "data/ir_cron.xml",
        "views/res_config_settings_views.xml",
    ],
    "excludes": [
        "web_enterprise",
    ],
    "auto_install": False,
    "application": False,
}
