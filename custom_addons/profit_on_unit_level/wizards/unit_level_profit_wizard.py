from collections import defaultdict
from odoo import models, fields, api, _
from datetime import datetime, timedelta


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    salesperson_id = fields.Many2one('res.users', string='Salesperson', related='order_id.user_id', readonly=True)

    def action_get_purchase(self):
        self.ensure_one()
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': self.order_id.id,
            'target': 'new',
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    salesperson_id = fields.Many2one('res.users', string='Salesperson', related='order_id.user_id', readonly=True)

    def action_get_sale(self):
        self.ensure_one()
        return {
            'name': _('Sale Order'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': self.order_id.id,
            'target': 'new',
        }


class SaleOrderLine(models.Model):
    _inherit = 'pos.order.line'

    salesperson_id = fields.Many2one('res.users', string='Salesperson', related='order_id.user_id', readonly=True)

    def action_get_pos_sale(self):
        self.ensure_one()
        return {
            'name': _('POS Sale Order'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id': self.order_id.id,
            'target': 'new',
        }


class ProductDetailsWizard(models.TransientModel):
    _name = 'product.level.overview.wizard'
    _description = 'Product Level Overview'

    product_id = fields.Many2one('product.product', string="Product")

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    currency_id = fields.Many2one("res.currency", string="Company Currency")

    purchase_ids = fields.Many2many('purchase.order.line', string="Purchases")
    sale_ids = fields.Many2many('sale.order.line', string="Sales")
    pos_sale_ids = fields.Many2many('pos.order.line', string="Sales")


class UnitLevelProfitLine(models.TransientModel):
    _name = 'unit.level.profit.line'
    _description = 'Unit Level Profit Line'

    unit_level_profit_id = fields.Many2one('unit.level.profit', string="Unit Level Profit Reference",
                                           ondelete="cascade")
    product_id = fields.Many2one('product.product', string="Product")
    currency_id = fields.Many2one("res.currency", string="Company Currency")
    average_purchase_price = fields.Monetary(string="Average Purchase Price", currency_field='currency_id')
    average_sales_price = fields.Monetary(string="Average Sales Price", currency_field='currency_id')
    profit_per_unit = fields.Monetary(string="Profit Per Unit", currency_field='currency_id')
    units_sold = fields.Integer(string="Units Sold")

    def action_check_product_details(self):
        self.ensure_one()

        start_date = self.unit_level_profit_id.start_date
        end_date = self.unit_level_profit_id.end_date

        domain = [
            ('product_id', '=', self.product_id.id),
            ('order_id.date_order', '>=', start_date),
            ('order_id.date_order', '<=', end_date),
        ]

        purchase_domain = domain + [('state', 'in', ['purchase', 'done'])]
        sales_domain = domain + [('state', 'in', ['sale', 'done'])]
        pos_sales_domain = domain + [('refunded_orderline_id', '=', False)]

        sale_ids = self.env['sale.order.line'].search(sales_domain).ids
        pos_sale_ids = self.env['pos.order.line'].search(pos_sales_domain).ids
        purchase_ids = self.env['purchase.order.line'].search(purchase_domain).ids
        if len(purchase_ids) == 0:
            domain = [('product_id', '=', self.product_id.id), ('state', 'in', ['purchase', 'done'])]
            purchase_ids = self.env['purchase.order.line'].search(domain).ids

        sale_and_pos_sale_ids = [(0, 0, {'sale_order_line_id': sale_id}) for sale_id in sale_ids]
        sale_and_pos_sale_ids += [(0, 0, {'pos_order_line_id': pos_sale_id}) for pos_sale_id in pos_sale_ids]

        return {
            'name': _('Product Details'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'product.level.overview.wizard',
            'target': 'new',
            'context': {
                'default_start_date': start_date,
                'default_end_date': end_date,
                'default_product_id': self.product_id.id,
                'default_currency_id': self.currency_id.id,
                'default_purchase_ids': purchase_ids,
                'default_sale_ids': sale_ids,
                'default_pos_sale_ids': pos_sale_ids,
            }
        }


class UnitLevelProfit(models.TransientModel):
    _name = 'unit.level.profit'
    _description = 'Unit Level Profit'

    time_range_selection = fields.Selection([
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('this_month', 'This Month'),
        ('last_month', 'Last Month'),
        ('current_year', 'Current Year'),
        ('last_year', 'Last Year'),
        ('custom', 'Custom Range'),
    ], string="Time Range", default='last_month', required=True)

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    @api.onchange('time_range_selection')
    def _onchange_time_range_selection(self):
        today = datetime.today()
        if self.time_range_selection == 'today':
            self.start_date = today
            self.end_date = today
        elif self.time_range_selection == 'yesterday':
            yesterday = today - timedelta(days=1)
            self.start_date = yesterday
            self.end_date = yesterday
        elif self.time_range_selection == 'this_month':
            self.start_date = today.replace(day=1)
            self.end_date = today
        elif self.time_range_selection == 'last_month':
            first_day_last_month = today.replace(day=1) - timedelta(days=1)
            self.start_date = first_day_last_month.replace(day=1)
            self.end_date = first_day_last_month
        elif self.time_range_selection == 'current_year':
            self.start_date = today.replace(month=1, day=1)
            self.end_date = today
        elif self.time_range_selection == 'last_year':
            self.start_date = today.replace(year=today.year - 1, month=1, day=1)
            self.end_date = today.replace(year=today.year - 1, month=12, day=31)
        elif self.time_range_selection == 'custom':
            pass

    currency_id = fields.Many2one("res.currency", string="Company Currency", compute="_compute_currency_id")
    product_profit_ids = fields.One2many('unit.level.profit.line', 'unit_level_profit_id', string="Product Profits")
    total_expenses = fields.Monetary(string="Total Expenses", currency_field='currency_id', readonly=True)
    average_unit_profit = fields.Monetary(string="Average Unit Profit", currency_field='currency_id',
                                          compute='_compute_average_unit_profit', readonly=True)

    # The products listed here are considered for profit calculation
    product_category_ids = fields.Many2many('product.category', 'product_category_rel', string="Product Categories")

    # The products listed in this category are deducted from the profit calculation
    expense_category_ids = fields.Many2many('product.category', 'expense_category_rel',
                                            string="Product Expense Categories")

    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.env.company.currency_id

    @api.depends('product_profit_ids.profit_per_unit')
    def _compute_average_unit_profit(self):
        total_profit = sum(line.profit_per_unit for line in self.product_profit_ids)
        total_units = sum(line.units_sold for line in self.product_profit_ids)
        self.average_unit_profit = total_profit / total_units if total_units else 0

    def _get_product_profits(self):
        if not self.start_date or not self.end_date:
            return []

        product_sales = defaultdict(list)
        product_purchases = defaultdict(list)
        product_profits = []

        company_currency_id = self.env.company.currency_id

        # Assumptions:
        # 1. The products are in a different product category than the products
        # 2. The purchase expenses (trucks, documentation) are only factored for purchases
        #    -> Expenses (like trucks and documentation) on sales are not considered
        # 3. The company expenses are divided by the total units sold

        # Define the period for sales and purchases
        date_domain = [('date', '>=', self.start_date), ('date', '<=', self.end_date)]

        # Calculate total expenses within the period
        expense_domain = date_domain + [('state', 'in', ['purchase', 'done'])]
        hr_expenses = sum(self.env['hr.expense'].search(expense_domain).mapped('total_amount'))

        # 1. Compute sales
        sales_domain = date_domain + [('payment_state', '!=', 'reversed')]
        invoices = self.env["account.move"].search(sales_domain).filtered(lambda x: x.move_type == "out_invoice")
        for invoice in invoices:
            for line in invoice.invoice_line_ids.filtered(lambda line: line.quantity > 0):
                if line.product_id.product_tmpl_id.categ_id.id in self.product_category_ids.ids:
                    price_total = abs(line.currency_id._convert(line.amount_currency, to_currency=company_currency_id))
                    product_sales[line.product_id.id].append({
                        'price_total': price_total,
                        'units_sold': line.quantity,
                    })

        # 2. Compute and append POS sales -> Filter for those without invoice
        date_domain = [('order_id.date_order', '>=', self.start_date), ('order_id.date_order', '<=', self.end_date)]
        pos_sales_domain = date_domain + [('order_id.to_invoice', '=', True), ('qty', '>', 0)]
        pos_sales_data = self.env['pos.order.line'].search(pos_sales_domain)
        # We need to filter the POS Sales that are already invoiced -> Otherwise they are twice in the Sales
        for sale in pos_sales_data:
            price_total = sale['currency_id']._convert(sale['price_subtotal'], to_currency=company_currency_id)
            product_sales[sale.product_id.id].append({'price_total': price_total, 'units_sold': sale.qty})

        total_units_sold = sum([sum(sale['units_sold'] for sale in product) for product in product_sales.values()])
        expense_per_unit = hr_expenses / total_units_sold if total_units_sold else 0

        for product_id, sales in product_sales.items():
            total_sale_units = sum(sale['units_sold'] for sale in sales)
            total_sale_price = sum(sale['price_total'] for sale in sales)
            average_sales_price = total_sale_price / total_sale_units if total_sale_units else 0

            # 3. Compute Purchases <-> If no purchase is available in time frame, take all purchases
            date_domain = [('date', '>=', self.start_date), ('date', '<=', self.end_date)]
            product_domain = [('invoice_line_ids.product_id', '=', product_id)]
            purchase_domain = date_domain + product_domain

            bills = self.env["account.move"].search(purchase_domain).filtered(lambda x: x.move_type == "in_invoice")
            if len(bills) == 0:
                bills = self.env["account.move"].search(product_domain).filtered(lambda x: x.move_type == "in_invoice")

            for bill in bills:
                product_lines = bill.invoice_line_ids.filtered(
                    lambda line: line.quantity > 0 and line.product_id.id == product_id)
                all_product_lines = bill.invoice_line_ids.filtered(
                    lambda line: line.product_id.product_tmpl_id.categ_id.id in self.product_category_ids.ids)
                expense_lines = bill.invoice_line_ids.filtered(
                    lambda line: line.product_id.product_tmpl_id.categ_id.id in self.product_category_ids.ids)

                total_purchase_quantity = sum(line.quantity for line in all_product_lines)
                total_bill_expense = sum(line.price_subtotal for line in expense_lines)

                for line in product_lines:
                    expenses = total_bill_expense * (line.quantity /
                                                     total_purchase_quantity) if total_purchase_quantity else 0
                    price_total = line.currency_id._convert(line.amount_currency, to_currency=company_currency_id)
                    product_purchases[line.product_id.id].append({
                        'price_total': price_total,
                        'units_sold': line.quantity,
                        'expenses': expenses
                    })

            # Compute profit per unit, adjusted for expenses
            purchases = product_purchases.get(product_id)
            if purchases is not None:
                total_purchase_units = sum(purchase['units_sold'] for purchase in purchases)
                total_purchase_price = sum(purchase['price_total'] for purchase in purchases)
                average_purchase_price = total_purchase_price / total_purchase_units if total_purchase_units else 0
            else:
                average_purchase_price = 0

            profit_per_unit = average_sales_price - average_purchase_price - expense_per_unit

            product_profits.append({
                'product_id': product_id,
                'average_purchase_price': average_purchase_price,
                'average_sales_price': average_sales_price,
                'profit_per_unit': profit_per_unit,
                'units_sold': total_sale_units,
            })

        return product_profits

    @api.onchange('time_range_selection', 'start_date', 'end_date')
    def _compute_product_profits(self):
        ProfitLine = self.env['unit.level.profit.line']
        self.product_profit_ids = [(5, 0, 0)]  # Clear existing lines
        for data in self._get_product_profits():
            self.product_profit_ids += ProfitLine.create({'currency_id': self.env.company.currency_id.id, **data})
