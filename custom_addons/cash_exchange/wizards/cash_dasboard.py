from odoo import models, fields, api
from datetime import datetime


class CashDashboard(models.TransientModel):
    _name = 'cash.dashboard.wizard'
    _description = 'Cash Dashboard'
