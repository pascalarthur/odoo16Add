from odoo import models, fields, api
import base64
from io import BytesIO
import xlsxwriter


class POSEmployeeReportWizard(models.TransientModel):
    _name = 'pos.employee.report.wizard'
    _description = 'POS Employee Report Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    name = fields.Char(string='Name', related='employee_id.name', readonly=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    excel_file = fields.Binary(string='Excel File', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)

    def create_report(self):
        self.ensure_one()
        # Create a file in memory
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # Define Excel format
        bold_format = workbook.add_format({'bold': True})

        # Write the headers
        worksheet.write('A1', 'User', bold_format)
        worksheet.write('B1', 'Order Date', bold_format)
        worksheet.write('C1', 'Order ID', bold_format)
        worksheet.write('D1', 'Total', bold_format)

        row = 1

        # Fetch POS orders
        pos_orders = self.env['pos.order'].search([
            ('date_order', '>=', self.start_date),
            ('date_order', '<=', self.end_date),
            ('employee_id', '=', self.employee_id.id),
        ])

        # Write POS orders to Excel
        for order in pos_orders:
            worksheet.write(row, 0, order.employee_id.user_id.name)
            worksheet.write(row, 1, str(order.date_order))
            worksheet.write(row, 2, order.name)
            worksheet.write(row, 3, order.amount_total)
            row += 1

        # Fetch Sales orders
        sales_orders = self.env['sale.order'].search([('date_order', '>=', self.start_date),
                                                      ('date_order', '<=', self.end_date),
                                                      ('user_id', '=', self.employee_id.user_id.id)])

        # Write Sales orders to Excel
        for order in sales_orders:
            worksheet.write(row, 0, order.user_id.name)  # Assuming you have a field for employee
            worksheet.write(row, 1, str(order.date_order))
            worksheet.write(row, 2, order.name)
            worksheet.write(row, 3, order.amount_total)
            row += 1

        workbook.close()
        output.seek(0)

        self.excel_file = base64.b64encode(output.read())
        self.file_name = f'Sales_Report_{self.start_date}_{self.end_date}_{self.employee_id.user_id.name}.xlsx'

        return {
            'type':
            'ir.actions.act_url',
            'url':
            '/web/content/?model=pos.employee.report.wizard&id=%s&field=excel_file&filename_field=file_name&download=true'
            % self.id,
            'target':
            'self',
        }
