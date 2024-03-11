from collections import defaultdict
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

    def _create_worksheet(self, workbook, name):
        worksheet = workbook.add_worksheet(name)
        bold_format = workbook.add_format({'bold': True})

        worksheet.write('A1', 'User', bold_format)
        worksheet.write('B1', 'Order Date', bold_format)
        worksheet.write('C1', 'Order ID', bold_format)
        worksheet.write('D1', 'Total', bold_format)
        worksheet.write('E1', 'Currency', bold_format)
        worksheet.write('F1', 'Customer', bold_format)
        worksheet.write('G1', 'Payment Method', bold_format)

        return worksheet

    def _write_order_line(self, worksheet, row, order, name):
        worksheet.write(row, 0, name)
        worksheet.write(row, 1, str(order.date_order))
        worksheet.write(row, 2, order.name)
        worksheet.write(row, 3, order.amount_total)
        worksheet.write(row, 4, order.currency_id.name)
        if order.partner_id:
            worksheet.write(row, 5, order.partner_id.name)
        if "payment_ids" in order and order.payment_ids:
            worksheet.write(row, 6, order.payment_ids.payment_method_id.name)

    def _create_pos_sales_report(self, workbook):
        worksheet = self._create_worksheet(workbook, 'POS Sales')

        pos_orders = self.env['pos.order'].search([
            ('date_order', '>=', self.start_date),
            ('date_order', '<=', self.end_date),
            ('employee_id', '=', self.employee_id.id),
        ])
        for row, order in enumerate(pos_orders):
            self._write_order_line(worksheet, row + 1, order, order.employee_id.user_id.name)

    def _create_sale_sales_report(self, workbook):
        worksheet = self._create_worksheet(workbook, 'Sale Sales')
        row = 1

        # Fetch Sales orders
        sales_orders = self.env['sale.order'].search([('date_order', '>=', self.start_date),
                                                      ('date_order', '<=', self.end_date),
                                                      ('user_id', '=', self.employee_id.user_id.id)])
        for row, order in enumerate(sales_orders):
            self._write_order_line(worksheet, row + 1, order, order.user_id.name)

    def _create_sales_report(self, workbook):
        worksheet = self._create_worksheet(workbook, 'Sales')

        row = 1
        # Fetch POS orders
        pos_orders = self.env['pos.order'].search([
            ('date_order', '>=', self.start_date),
            ('date_order', '<=', self.end_date),
            ('employee_id', '=', self.employee_id.id),
        ])
        for order in pos_orders:
            self._write_order_line(worksheet, row, order, order.employee_id.user_id.name)
            row += 1

        # Fetch Sales orders
        sales_orders = self.env['sale.order'].search([('date_order', '>=', self.start_date),
                                                      ('date_order', '<=', self.end_date),
                                                      ('user_id', '=', self.employee_id.user_id.id)])
        for order in sales_orders:
            self._write_order_line(worksheet, row, order, order.user_id.name)
            row += 1

    def _create_sales_report_by_product(self, workbook):
        worksheet = workbook.add_worksheet('Sales by Product')
        bold_format = workbook.add_format({'bold': True})

        worksheet.write('A1', 'Product', bold_format)
        worksheet.write('B1', 'Quantity', bold_format)
        worksheet.write('C1', 'Total', bold_format)
        worksheet.write('D1', 'Currency', bold_format)

        row = 1

        # Fetch POS orders
        pos_orders = self.env['pos.order'].search([
            ('date_order', '>=', self.start_date),
            ('date_order', '<=', self.end_date),
            ('employee_id', '=', self.employee_id.id),
        ])

        # Fetch Sales orders
        sales_orders = self.env['sale.order'].search([
            ('date_order', '>=', self.start_date),
            ('date_order', '<=', self.end_date),
            ('user_id', '=', self.employee_id.user_id.id),
        ])

        # Aggregate data
        data = defaultdict(list)
        for order in pos_orders:
            for line in order.lines:
                data[line.product_id.display_name].append({
                    'quantity': line.qty,
                    'total': line.price_subtotal,
                    'currency': order.currency_id.name,
                })

        for order in sales_orders:
            for line in order.order_line:
                data[line.product_id.display_name].append({
                    'quantity': line.product_uom_qty,
                    'total': line.price_subtotal,
                    'currency': order.currency_id.name,
                })

        # Write data to worksheet
        for product, order_list in data.items():
            worksheet.write(row, 0, product)
            for order in order_list:
                worksheet.write(row, 1, order['quantity'])
                worksheet.write(row, 2, order['total'])
                worksheet.write(row, 3, order['currency'])
                row += 1

    def create_report(self):
        self.ensure_one()
        # Create a file in memory
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        self._create_sales_report(workbook)
        self._create_sale_sales_report(workbook)
        self._create_pos_sales_report(workbook)
        self._create_sales_report_by_product(workbook)

        workbook.close()
        output.seek(0)

        self.excel_file = base64.b64encode(output.read())
        self.file_name = f'Sales_Report_{self.start_date}_{self.end_date}_{self.employee_id.user_id.name}.xlsx'

        download_url = '/web/content/?model=pos.employee.report.wizard&id=%s&field=excel_file&filename_field=file_name&download=true' % self.id
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }
