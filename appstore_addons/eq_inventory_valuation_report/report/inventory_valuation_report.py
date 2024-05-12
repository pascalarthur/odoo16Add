# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

from collections import defaultdict
import datetime
from typing import Any, Dict, Optional
import pytz
from operator import itemgetter
from itertools import groupby
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_round


class eq_inventory_valuation_report_inventory_valuation_report(models.AbstractModel):
    _name = 'report.eq_inventory_valuation_report.inventory_valuation_report'
    _description = 'Report Inventory Valuation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name(
            'eq_inventory_valuation_report.inventory_valuation_report')
        record_id = data['form']['id'] if data and data['form'] and data['form']['id'] else docids[0]
        records = self.env['wizard.inventory.valuation'].browse(record_id)
        return {
            'doc_model': report.model,
            'docs': records,
            'data': data,
            'get_beginning_inventory': self._get_beginning_inventory,
            'get_products': self._get_products,
            'get_product_sale_qty': self.get_product_sale_qty,
            'get_location_wise_product': self.get_location_wise_product,
            'get_warehouse_wise_location': self.get_warehouse_wise_location,
            'get_product_valuation': self.get_product_valuation
        }

    def get_warehouse_wise_location(self, record, warehouse):
        stock_location_obj = self.env['stock.location']
        location_ids = stock_location_obj.search([('location_id', 'child_of', warehouse.view_location_id.id)])
        final_location_ids = record.location_ids & location_ids
        return final_location_ids or location_ids

    def get_location_wise_product(
            self, record, inventory_by_location_and_product_start: Dict[int, Dict[int, int]]) -> Dict[int, dict]:
        qtys_dict = defaultdict(lambda: defaultdict(dict))
        for location_id, product_qtys in inventory_by_location_and_product_start.items():
            for product, location_begning_qty in product_qtys.items():
                product_sale_qty = self.get_product_sale_qty(record, product, location_id)

                product_sale_qty["product_qty_begin"] = location_begning_qty
                product_sale_qty["product_qty_end"] = sum(product_sale_qty.values())

                if sum(abs(x) for x in product_sale_qty.values()):
                    qtys_dict[location_id][product] = product_sale_qty

        return qtys_dict

    def convert_withtimezone(self, userdate):
        timezone = pytz.timezone(self._context.get('tz') or 'UTC')
        if timezone:
            utc = pytz.timezone('UTC')
            end_dt = timezone.localize(fields.Datetime.from_string(userdate), is_dst=False)
            end_dt = end_dt.astimezone(utc)
            return end_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return userdate.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def _filter_purchased_product_qty(self, product_ids):
        domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
            ('product_id', 'in', product_ids.ids),
        ]
        purchased_products = self.env['purchase.order.line'].search(domain).mapped("product_id").ids
        return product_ids.filtered(lambda product_id: product_id.id in purchased_products)

    def _get_products(self, category_ids: Optional[Any]):
        domain = [('type', '=', 'product')]
        if category_ids:
            domain.append(('categ_id', 'in', category_ids.ids))
        product_ids = self.env['product.product'].search(domain)
        return self._filter_purchased_product_qty(product_ids)

    def get_locations(self, company_id, warehouse):
        location_ids = [warehouse.view_location_id.id]
        domain = [('company_id', '=', company_id.id), ('usage', '=', 'internal'),
                  ('location_id', 'child_of', location_ids)]
        return self.env['stock.location'].sudo().search(domain)

    def get_inventory_at_date(self, date, location_id, category_ids: Optional[Any], is_start_of_day: bool = True):
        date = date if is_start_of_day is False else date + datetime.timedelta(days=1)
        date = self.convert_withtimezone(date)

        product_ids = self._get_products(category_ids)

        domain = [
            ('date', '<', date),
            ('state', '=', 'done'),
            ('product_id', 'in', product_ids.ids),
            '|',
            ('location_id', '=', location_id.id),
            ('location_dest_id', '=', location_id.id),
        ]
        stock_moves = self.env['stock.move.line'].search(domain)

        inventory_by_product = defaultdict(lambda: 0)
        for move in stock_moves:
            if move.location_id.id == location_id.id:
                inventory_by_product[move.product_id.id] -= move.quantity
            if move.location_dest_id.id == location_id.id:
                inventory_by_product[move.product_id.id] += move.quantity
        return inventory_by_product

    def get_product_sale_qty(self, record, product, location):
        location = tuple(location.ids)
        start_date = record.start_date.strftime("%Y-%m-%d") + ' 00:00:00'
        end_date = record.end_date.strftime("%Y-%m-%d") + ' 23:59:59'

        self._cr.execute(
            '''
                        SELECT
                            sum((
                            CASE WHEN spt.code in ('outgoing') AND smline.location_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory'
                            THEN -(smline.quantity * pu.factor / pu2.factor)
                            ELSE 0.0
                            END
                            )) AS product_qty_out,
                                sum((
                            CASE WHEN spt.code in ('incoming') AND smline.location_dest_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory'
                            THEN (smline.quantity * pu.factor / pu2.factor)
                            ELSE 0.0
                            END
                            )) AS product_qty_in,

                            sum((
                            CASE WHEN (spt.code ='internal') AND smline.location_dest_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory'
                            THEN (smline.quantity * pu.factor / pu2.factor)
                            WHEN (spt.code ='internal' OR spt.code is null) AND smline.location_id in %s AND sourcel.usage !='inventory' AND destl.usage !='inventory'
                            THEN -(smline.quantity * pu.factor / pu2.factor)
                            ELSE 0.0
                            END
                            )) AS product_qty_internal,

                            sum((
                            CASE WHEN sourcel.usage = 'inventory' AND smline.location_dest_id in %s
                            THEN  (smline.quantity * pu.factor / pu2.factor)
                            WHEN destl.usage ='inventory' AND smline.location_id in %s
                            THEN -(smline.quantity * pu.factor / pu2.factor)
                            ELSE 0.0
                            END
                            )) AS product_qty_adjustment
                        FROM product_product pp
                        LEFT JOIN stock_move sm ON (sm.product_id = pp.id and sm.date >= %s and sm.date <= %s and sm.state = 'done' and sm.location_id != sm.location_dest_id)
                        LEFT JOIN stock_move_line smline ON (smline.product_id = pp.id and smline.state = 'done' and smline.location_id != smline.location_dest_id and smline.move_id = sm.id)
                        LEFT JOIN stock_picking sp ON (sm.picking_id=sp.id)
                        LEFT JOIN stock_picking_type spt ON (spt.id=sp.picking_type_id)
                        LEFT JOIN stock_location sourcel ON (smline.location_id=sourcel.id)
                        LEFT JOIN stock_location destl ON (smline.location_dest_id=destl.id)
                        LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                        LEFT JOIN uom_uom pu ON (pt.uom_id=pu.id)
                        LEFT JOIN uom_uom pu2 ON (smline.product_uom_id=pu2.id)
                        WHERE pp.id in %s
                        GROUP BY pt.categ_id, pp.id order by pt.categ_id
                        ''',
            (location, location, location, location, location, location, start_date, end_date, tuple([product])))
        values = self._cr.dictfetchall()
        if record.group_by_categ and not location:
            sort_by_categories = sorted(values, key=itemgetter('categ_id'))
            records_by_categories = dict(
                (k, [v for v in itr]) for k, itr in groupby(sort_by_categories, itemgetter('categ_id')))
            return records_by_categories
        else:
            return values[0]

    def get_product_valuation(self, record, product_id, quantity: float, warehouse: str, op_type: str) -> float:
        if not quantity:
            return 0.0
        product_price = self.env['decimal.precision'].precision_get('Product Price')
        end_date = record.end_date.strftime("%Y-%m-%d") + ' 23:59:59'
        domain = [('product_id', '=', product_id.id), ('company_id', '=', record.company_id.id),
                  ('warehouse_id', '=', warehouse.id)]

        if op_type == 'beg':
            domain.append(('create_date', '<', record.start_date))
        if op_type == 'in':
            domain += [('create_date', '>=', record.start_date), ('create_date', '<=', end_date), '|',
                       ('stock_move_id', '=', False), ('stock_move_id.picking_code', '=', 'incoming')]
        if op_type == 'out':
            domain += [('create_date', '>=', record.start_date), ('create_date', '<=', end_date), '|',
                       ('stock_move_id', '=', False), ('stock_move_id.picking_code', '=', 'outgoing')]
        if op_type == 'adj':
            domain += [('create_date', '>=', record.start_date), ('create_date', '<=', end_date), '|',
                       ('stock_move_id', '=', False), ('stock_move_id.is_inventory', '!=', False)]
        valuation_layer_ids = self.env['stock.valuation.layer'].search(domain)
        value = sum(valuation_layer_ids.mapped('value'))
        if op_type in ['int', 'final']:
            value = quantity * product_id.standard_price
        return float_round(value, precision_digits=product_price)
