from odoo import api, models, fields
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    turnover_last_month_pos = fields.Monetary(string="Turnover POS", compute="_compute_last_month_pos",
                                              currency_field='currency_id')
    turnover_last_month_sales = fields.Monetary(string="Turnover Sales", compute="_compute_turnover_last_month_sales",
                                                currency_field='currency_id')

    def _compute_last_month_pos(self):
        start_date = fields.Date.today().replace(day=1)
        end_date = start_date + relativedelta(months=1, days=-1)
        for employee_id in self:
            pos_orders = self.env['pos.order'].search([
                ('date_order', '>=', start_date),
                ('date_order', '<=', end_date),
                ('employee_id', '=', employee_id.id),
            ])

            employee_id.turnover_last_month_pos = sum(pos_orders.mapped("amount_total"))

    def _compute_turnover_last_month_sales(self):
        start_date = fields.Date.today().replace(day=1)
        end_date = start_date + relativedelta(months=1, days=-1)
        for employee_id in self:
            sales_orders = self.env['sale.order'].search([('date_order', '>=', start_date),
                                                          ('date_order', '<=', end_date),
                                                          ('user_id', '=', employee_id.user_id.id)])
            employee_id.turnover_last_month_sales = sum(sales_orders.mapped("amount_total"))

    def action_get_employee_report(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "pos.employee.report.wizard",
            "views": [[False, "form"]],
            "target": "new",
            "context": {
                "default_employee_id": self.id,
            },
        }

