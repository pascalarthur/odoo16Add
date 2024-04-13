from collections import defaultdict
from odoo import models, fields, api, _
from datetime import datetime, timedelta


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

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


class ProductDetailsWizard(models.TransientModel):
    _name = 'product.level.overview.wizard'
    _description = 'Product Level Overview'

    product_id = fields.Many2one('product.product', string="Product")

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    currency_id = fields.Many2one("res.currency", string="Company Currency")

    sale_ids = fields.Many2many('sale.order.line', string="Sales")
    purchase_ids = fields.Many2many('purchase.order.line', string="Purchases")


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

        # Define domain for sales and purchases within the time range and for the product
        sales_domain = [
            ('product_id', '=', self.product_id.id),
            ('state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', start_date),
            ('order_id.date_order', '<=', end_date),
        ]

        purchase_domain = [
            ('product_id', '=', self.product_id.id),
            ('state', 'in', ['purchase', 'done']),
            ('order_id.date_order', '>=', start_date),
            ('order_id.date_order', '<=', end_date),
        ]

        sale_ids = self.env['sale.order.line'].search(sales_domain).ids
        purchase_ids = self.env['purchase.order.line'].search(purchase_domain).ids

        # Action to return
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
                'default_sale_ids': sale_ids,
                'default_purchase_ids': purchase_ids,
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

    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.env.company.currency_id

    @api.depends('product_profit_ids.profit_per_unit')
    def _compute_average_unit_profit(self):
        total_profit = sum(line.profit_per_unit for line in self.product_profit_ids)
        total_units = sum(line.units_sold for line in self.product_profit_ids)
        self.average_unit_profit = total_profit / total_units if total_units else 0

    def _get_product_profits(self):
        # Define the period for sales and purchases
        date_domain = [('order_id.date_order', '>=', self.start_date), ('order_id.date_order', '<=', self.end_date)]
        sales_domain = date_domain + [('state', 'in', ['sale', 'done']), ('product_id.type', '=', 'product')]
        purchase_domain = date_domain + [('state', 'in', ['purchase', 'done'])]
        expense_domain = [('date', '>=', self.start_date), ('date', '<=', self.end_date),
                          ('state', 'in', ['purchase', 'done'])]

        # Calculate total expenses within the period
        total_expenses = sum(self.env['hr.expense'].search(expense_domain).mapped('total_amount'))

        # Aggregate sales data by product
        sales_data = self.env['sale.order.line'].search(sales_domain)
        total_units_sold = sum(sales_data.mapped("product_uom_qty"))
        expense_per_unit = total_expenses / total_units_sold if total_units_sold else 0

        product_sales = defaultdict(list)

        for sale in sales_data:
            price_total = sale['currency_id']._convert(sale['price_total'], to_currency=self.env.company.currency_id)
            product_sales[sale.product_id.id].append({'price_total': price_total, 'units_sold': sale.product_uom_qty})

        product_profits = []
        for product_id, sales in product_sales.items():
            units_sold = sum(sale['units_sold'] for sale in sales)
            price_total = sum(sale['price_total'] for sale in sales)

            average_sales_price = price_total / units_sold if units_sold else 0

            # Aggregate purchase data for the same product
            purchase_lines = self.env['purchase.order.line'].search(purchase_domain + [('product_id', '=', product_id)])
            total_purchase = sum(
                line.currency_id._convert(line.price_subtotal, to_currency=self.env.company.currency_id)
                for line in purchase_lines)
            total_qty_purchased = sum(line.product_qty for line in purchase_lines)
            average_purchase_price = total_purchase / total_qty_purchased if total_qty_purchased else 0

            # Compute profit per unit, adjusted for expenses
            profit_per_unit = average_sales_price - average_purchase_price - expense_per_unit

            product_profits.append({
                'product_id': product_id,
                'average_purchase_price': average_purchase_price,
                'average_sales_price': average_sales_price,
                'profit_per_unit': profit_per_unit,
                'units_sold': units_sold,
            })

        return product_profits

    @api.onchange('time_range_selection', 'start_date', 'end_date')
    def _compute_product_profits(self):
        ProfitLine = self.env['unit.level.profit.line']
        self.product_profit_ids = [(5, 0, 0)]  # Clear existing lines
        for data in self._get_product_profits():
            self.product_profit_ids += ProfitLine.create({'currency_id': self.env.company.currency_id.id, **data})
