import os
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
import base64

import pandas as pd


class wizard_inventory_valuation(models.TransientModel):
    _name = 'wizard.inventory.valuation'
    _description = 'Wizard Inventory Valuation'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id,
                                 readonly=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouse')
    location_ids = fields.Many2many('stock.location', string='Location')
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    filter_by = fields.Selection([('product', 'Product'), ('category', 'Category')], string="Filter By")
    group = fields.Boolean(default=False, string="Group")
    group_by = fields.Selection([('product', 'Product'), ('category', 'Category')], string="Group By")
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    name = fields.Char(string='File Name', readonly=True)
    data = fields.Binary(string='File', readonly=True)
    product_ids = fields.Many2many('product.product', string="Products")
    category_ids = fields.Many2many('product.category', string="Categories")

    @api.onchange('company_id')
    def onchange_company_id(self):
        domain = [('id', 'in', self.env.user.company_ids.ids)]
        if self.company_id:
            self.warehouse_ids = False
            self.location_ids = False
        return {'domain': {'company_id': domain}}

    @api.onchange('warehouse_ids')
    def onchange_warehouse_ids(self):
        addtional_ids = []
        if self.warehouse_ids:
            for warehouse in self.warehouse_ids:
                addtional_ids.extend([
                    y.id for y in self.env['stock.location'].search([(
                        'location_id', 'child_of', warehouse.view_location_id.id), ('usage', '=', 'internal')])
                ])
            self.location_ids = False
        return {'domain': {'location_ids': [('id', 'in', addtional_ids)]}}

    def check_date_range(self):
        if self.end_date < self.start_date:
            raise ValidationError(_('End Date should be greater than Start Date.'))

    @api.onchange('filter_by')
    def onchange_filter_by(self):
        self.product_ids = False
        self.category_ids = False

    def print_report(self):
        self.check_date_range()
        datas = {
            'form': {
                'company_id': self.company_id.id,
                'warehouse_ids': [y.id for y in self.warehouse_ids],
                'location_ids': self.location_ids.ids or False,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'id': self.id,
                'product_ids': self.product_ids.ids,
                'product_categ_ids': self.category_ids.ids
            },
        }
        return self.env.ref('eq_inventory_valuation_report.action_inventory_valuation_template').report_action(
            self, data=datas)

    def go_back(self):
        self.state = 'choose'
        return {
            'name': 'Inventory Valuation Report',
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new'
        }

    def get_locations(self, company_id, warehouse):
        domain = [('company_id', '=', company_id.id), ('usage', '=', 'internal'),
                  ('location_id', 'child_of', warehouse.view_location_id.ids)]
        return self.env['stock.location'].sudo().search(domain)

    def print_xls_report(self):
        self.check_date_range()
        xls_filename = 'inventory_valuation_report.xlsx'
        product_start_row = 5

        report_stock_inv_obj = self.env['report.eq_inventory_valuation_report.inventory_valuation_report']

        for warehouse in self.warehouse_ids:
            df_warehouse_meta = pd.DataFrame({
                "Company": [self.company_id.name],
                "Warehouse": [warehouse.name],
                "Start Date": [str(self.start_date)],
                "End Date": [str(self.end_date)]
            })

            location_ids = report_stock_inv_obj.get_warehouse_wise_location(self, warehouse)
            if len(location_ids) == 0:
                location_ids = self.get_locations(self.company_id, self.warehouse_ids)
            inventory_by_location = {
                loc: report_stock_inv_obj.get_inventory_at_date(self.start_date, loc, self.category_ids,
                                                                self.product_ids)
                for loc in location_ids
            }
            location_wise_data = report_stock_inv_obj.get_location_wise_product(self.start_date, self.end_date,
                                                                                inventory_by_location)

            df_data = pd.DataFrame({
                "Products": [],
                "Product Category": [],
                "Costing Method": [],
                "Location": [],
                "Beginning Qty": [],
                "Beginning Value": [],
                "Received Qty": [],
                "Received Value": [],
                "Sales Qty": [],
                "Sales Value": [],
                "Internal Qty": [],
                "Internal Value": [],
                "Adjustments Qty": [],
                "Adjustments Value": [],
                "Ending Qty": [],
                "Ending Value": []
            })

            for location_id, product_dicts in location_wise_data.items():
                for product, product_dict in product_dicts.items():
                    product_qty_begin_val = report_stock_inv_obj.get_product_valuation(
                        self, product, product_dict['product_qty_begin'], warehouse, 'beg')
                    product_qty_in_val = report_stock_inv_obj.get_product_valuation(self, product,
                                                                                    product_dict['product_qty_in'],
                                                                                    warehouse, 'in')
                    product_qty_out_val = report_stock_inv_obj.get_product_valuation(
                        self, product, product_dict['product_qty_out'], warehouse, 'out')
                    product_qty_internal_val = report_stock_inv_obj.get_product_valuation(
                        self, product, product_dict['product_qty_internal'], warehouse, 'int')
                    product_qty_adjustment_val = report_stock_inv_obj.get_product_valuation(
                        self, product, product_dict['product_qty_adjustment'], warehouse, 'adj')
                    product_qty_end_val = report_stock_inv_obj.get_product_valuation(
                        self, product, product_dict['product_qty_end'], warehouse, 'final')

                    cost_method = dict(product.categ_id.fields_get()['property_cost_method']['selection'])[
                        product.categ_id.property_cost_method]

                    # Append data to dataframe
                    df_data.loc[len(df_data)] = [
                        product.display_name, product.categ_id.complete_name, cost_method, location_id.display_name,
                        product_dict['product_qty_begin'], product_qty_begin_val, product_dict['product_qty_in'],
                        product_qty_in_val, product_dict['product_qty_out'], product_qty_out_val,
                        product_dict['product_qty_internal'], product_qty_internal_val,
                        product_dict['product_qty_adjustment'], product_qty_adjustment_val,
                        product_dict['product_qty_end'], product_qty_end_val
                    ]

            if self.group is True:
                if self.group_by == "product":
                    df_data = df_data.groupby(['Products', 'Product Category',
                                               'Costing Method']).sum().reset_index().drop("Location", axis=1)
                elif self.group_by == "category":
                    df_data = df_data.groupby(['Product Category',
                                               'Costing Method']).sum().reset_index().drop(['Products', 'Location'],
                                                                                           axis=1)

            with pd.ExcelWriter(os.path.join("/tmp", xls_filename), engine='xlsxwriter') as writer:
                workbook = writer.book

                header_merge_format = workbook.add_format({
                    'bold': True,
                    'align': 'center',
                    'valign': 'vcenter',
                    'font_size': 10,
                    'bg_color': '#D3D3D3',
                    'border': 1
                })

                df_warehouse_meta.to_excel(writer, sheet_name=warehouse.name, startrow=1, header=False, index=False)
                worksheet = writer.sheets[warehouse.name]  # worksheet is only created at to_excel()
                for col_num, value in enumerate(df_warehouse_meta.columns.values):
                    worksheet.write(0, col_num, value, header_merge_format)

                for col_num, value in enumerate(df_data.columns.values):
                    worksheet.write(product_start_row, col_num, value, header_merge_format)
                    col_width = max([len(str(s)) for s in df_data[value].values] + [len(value)])
                    worksheet.set_column(col_num, col_num, col_width + 1)  # Set column width
                df_data.to_excel(writer, sheet_name=warehouse.name, startrow=product_start_row + 1, header=False,
                                 index=False)

        self.write({
            'state': 'get',
            'data': base64.b64encode(open('/tmp/' + xls_filename, 'rb').read()),
            'name': xls_filename
        })
        return {
            'name': 'Inventory Valuation Report',
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new'
        }
