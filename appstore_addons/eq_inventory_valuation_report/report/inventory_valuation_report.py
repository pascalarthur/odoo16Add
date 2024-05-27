from collections import defaultdict
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from odoo import models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_round


class eq_inventory_valuation_report_inventory_valuation_report(models.AbstractModel):
    _name = 'report.eq_inventory_valuation_report.inventory_valuation_report'
    _description = 'Report Inventory Valuation Report'

    def get_warehouse_wise_location(self, record, warehouse):
        stock_location_obj = self.env['stock.location']
        location_ids = stock_location_obj.search([('location_id', 'child_of', warehouse.view_location_id.id)])
        final_location_ids = record.location_ids & location_ids
        return final_location_ids or location_ids

    def _get_products(self, category_ids: Optional[Any], product_ids: Optional[Any]):
        domain = [('type', '=', 'product')]
        if category_ids:
            domain.append(('categ_id', 'in', category_ids.ids))
        if product_ids:
            domain.append(('id', 'in', product_ids.ids))
        return self.env['product.product'].search(domain)

    def get_inventory_at_date(self, date, location_id, category_ids: Optional[Any], product_ids: Optional[Any],
                              is_start_of_day: bool = True):
        date = date if is_start_of_day is True else date + timedelta(days=1)

        product_ids = self._get_products(category_ids, product_ids)

        domain = [
            ('date', '<', date),
            ('state', '=', 'done'),
            ('product_id', 'in', product_ids.ids),
            '|',
            ('location_id', '=', location_id.id),
            ('location_dest_id', '=', location_id.id),
        ]

        inventory_by_product = defaultdict(lambda: 0)
        for move in self.env['stock.move.line'].search(domain):
            if move.location_id.id == location_id.id:
                inventory_by_product[move.product_id] -= move.quantity
            if move.location_dest_id.id == location_id.id:
                inventory_by_product[move.product_id] += move.quantity
        return inventory_by_product

    def get_product_sale_qty(self, start_date, end_date, product, location_id):
        domain = [
            ('date', '>=', start_date),
            ('date', '<=', end_date + timedelta(days=1)),
            ('state', '=', 'done'),
            ('product_id', '=', product.id),
            '|',
            ('location_id', '=', location_id.id),
            ('location_dest_id', '=', location_id.id),
        ]

        # Defaultdict is not possible, as we need all keys in the dict
        product_qtys = {
            x: 0.0
            for x in ["product_qty_in", "product_qty_out", "product_qty_internal", "product_qty_adjustment"]
        }
        for move in self.env['stock.move.line'].search(domain):
            product_uom_factor = move.product_id.product_tmpl_id.uom_id.factor
            move_uom_factor = move.product_uom_id.factor
            factor = product_uom_factor / move_uom_factor
            if move.location_id.usage != 'inventory' and move.location_dest_id.usage != 'inventory':
                if move.picking_id.picking_type_id.code == 'outgoing' and move.location_id.id == location_id.id:
                    product_qtys["product_qty_out"] -= move.quantity * factor
                elif move.picking_id.picking_type_id.code == 'incoming' and move.location_dest_id.id == location_id.id:
                    product_qtys["product_qty_in"] += move.quantity * factor
                elif move.picking_id.picking_type_id.code == 'internal':
                    if move.location_dest_id.id == location_id.id:
                        product_qtys["product_qty_internal"] += move.quantity * factor
                    if move.location_id.id == location_id.id:
                        product_qtys["product_qty_internal"] -= move.quantity * factor
            elif move.location_id.usage == 'inventory':
                if move.location_dest_id.id == location_id.id:
                    product_qtys["product_qty_adjustment"] += move.quantity * factor
                elif move.location_id.id == location_id.id:
                    product_qtys["product_qty_adjustment"] -= move.quantity * factor
        return product_qtys

    def get_location_wise_product(
            self, start_date, end_date,
            inventory_by_location_and_product_start: Dict[int, Dict[int, int]]) -> Dict[int, dict]:
        qtys_dict = defaultdict(lambda: defaultdict(dict))
        for location_id, product_qtys in inventory_by_location_and_product_start.items():
            for product_id, location_begning_qty in product_qtys.items():
                product_sale_qty = self.get_product_sale_qty(start_date, end_date, product_id, location_id)

                product_sale_qty["product_qty_begin"] = location_begning_qty
                product_sale_qty["product_qty_end"] = sum(product_sale_qty.values())

                if any([x != 0 for x in product_sale_qty.values()]):
                    qtys_dict[location_id][product_id] = product_sale_qty
        return qtys_dict

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
