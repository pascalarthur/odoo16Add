from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model
    def create_from_purchase_order_line(self, line, company, sale_order, allowed_company_ids: list):
        fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
        taxes = line.product_id.taxes_id.filtered(lambda r: not line.company_id or r.company_id == company)
        tax_ids = fpos.map_tax(taxes) if fpos else taxes
        quantity = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)

        price = line.price_unit or 0.0
        price = line.product_uom._compute_price(price, line.product_id.uom_id)
        vals = {
            'name': line.name,
            'customer_lead': line.product_id and line.product_id.sale_delay or 0.0,
            'tax_id': [(6, 0, tax_ids.ids)],
            'order_id': sale_order.id,
            'product_uom_qty': quantity,
            'product_id': line.product_id and line.product_id.id or False,
            'product_uom': line.product_id and line.product_id.uom_id.id or line.product_uom.id,
            'price_unit': price,
            'company_id': company.id
        }
        return self.with_context(allowed_company_ids=allowed_company_ids).sudo().create(vals)

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        for line in self.filtered(lambda line: line.qty_delivered_method == 'stock_move'):
            quantity = 0.0
            for move in line.move_ids:
                move_qty = move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                if move.state == 'done' and not move.scrapped and line.product_id == move.product_id:
                    if move.location_dest_id.usage == "customer" and not move.origin_returned_move_id or (
                            move.origin_returned_move_id and move.to_refund):
                        quantity += move_qty
                else:
                    quantity -= move_qty
            line.qty_delivered = quantity


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    inter_company_transfer = fields.Many2one('inter.company.transfer', copy=False)

    def action_view_internal(self):
        return self.inter_company_transfer.action_view_internal()

    def create_from_purchase_order(self, purchase_order, company_partner, partner_id, allowed_company_ids: list):
        if company_partner and not company_partner.intercompany_warehouse_id:
            raise ValidationError(_('Please select intercompany warehouse on  %s.') % company_partner.name)

        name = self.env['ir.sequence'].sudo().with_company(company_partner).next_by_code('sale.order') or '/'
        if purchase_order.inter_company_transfer.id and purchase_order.inter_company_transfer.pricelist_id.id:
            pricelist = purchase_order.inter_company_transfer.pricelist_id
        else:
            pricelist = partner_id.property_product_pricelist
        vals = {
            'name': name,
            'partner_invoice_id': partner_id.id,
            'date_order': purchase_order.date_order,
            'fiscal_position_id': partner_id.property_account_position_id.id,
            'payment_term_id': partner_id.property_payment_term_id.id,
            'user_id': False,
            'company_id': company_partner.id,
            'warehouse_id': company_partner.intercompany_warehouse_id.id,
            'client_order_ref': name,
            'partner_id': partner_id.id,
            'pricelist_id': pricelist.id,
            'inter_company_transfer': purchase_order.inter_company_transfer.id,
            'partner_shipping_id': partner_id.id
        }
        sale_order = self.with_context(allowed_company_ids=allowed_company_ids).sudo().create(vals)
        for line in purchase_order.order_line.sudo():
            self.env['sale.order.line'].sudo().create_from_purchase_order_line(line, company_partner, sale_order,
                                                                               allowed_company_ids)
        return sale_order

    def _create_stock_move_lines_for_tracking(self, move) -> None:
        move_qty = move.product_uom_qty
        for _ in range(int(move_qty)):
            if move.product_id.tracking == 'serial':
                seq = self.env['ir.sequence'].next_by_code('stock.lot.tracking.serial')
            elif move.product_id.tracking == 'lot':
                seq = self.env['ir.sequence'].next_by_code('stock.lot.tracking.lot')
            lot_name = move.env['stock.lot'].sudo().create({
                'name': seq,
                'product_id': move.product_id.id,
                'company_id': move.company_id.id,
                'ref': seq,
            })
            move.env['stock.move.line'].sudo().create({
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_uom_id': move.product_uom.id,
                'lot_id': lot_name.id,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                'quantity': 1,
            })
            move_qty -= 1

    def _create_purchase_order_from_sale_order(self):
        assert self.inter_company_transfer.id, 'Inter Transfer is not set'

        company_partner = self.env['res.company'].search([('partner_id', '=', self.partner_id.id)])
        purchase_order = self.env['purchase.order'].sudo().create_from_sale_order(self, company_partner,
                                                                                  self.env.company)
        if not self.client_order_ref:
            self.client_order_ref = purchase_order.name

        purchase_order.sudo().button_confirm()

        if self.env.user.company_id.validate_picking is True:
            for receipt in purchase_order.picking_ids:
                for move in receipt.move_ids_without_package:
                    if move.product_id.tracking == 'none':
                        move.write({'quantity': move.product_uom_qty})
                    else:
                        self._create_stock_move_lines_for_tracking(move)

                receipt.sudo()._action_done()

        if self.env.user.company_id.create_invoice is True:
            bill_id = purchase_order.create_bill_int(company_partner, is_sale_bill=True)

            if self.env.user.company_id.validate_invoice is True:
                bill_id.sudo().with_company(company_partner)._post()

            self.inter_company_transfer.update({
                'purchase_id': purchase_order.id or False,
                'currency_id': purchase_order.currency_id.id or False,
                'invoice_id': [(4, bill_id.id, 0)]
            })
            if not self.inter_company_transfer.to_warehouse.id:
                if company_partner and not company_partner.intercompany_warehouse_id:
                    raise ValidationError(_(f'Please Select Intercompany Warehouse On  {company_partner.name}.'))
                self.inter_company_transfer.update({'to_warehouse': company_partner.intercompany_warehouse_id.id})

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()

        is_correct_group = self.env.user.has_group('inter_company_transfer.group_ict_manager_access')
        company_partner_id = self.env['res.company'].search([('partner_id', '=', self.partner_id.id)])
        if company_partner_id.id and is_correct_group and self.env.user.company_id.allow_intercompany_transactions:
            trans_cls = self.env['inter.company.transfer']
            inter_lines = []

            for picking in self.picking_ids:
                for move in picking.move_ids_without_package:
                    if self.env.user.company_id.validate_picking:
                        move.write({'quantity': move.product_uom_qty})
                    if self.inter_company_transfer.id == False and self.client_order_ref == False:
                        inter_lines += self.env['inter.company.transfer.line'].create_from_move(move)

                if self.env.user.company_id.validate_picking:
                    picking._action_done()
                    for move in picking.move_ids_without_package:
                        for entry in move.account_move_ids:
                            entry.write({'partner_id': move.partner_id.id})

            if self.env.user.company_id.create_invoice:
                invoice = self._create_invoices()
                if self.env.user.company_id.validate_invoice:
                    invoice._post()

            if self.inter_company_transfer.id == False and self.client_order_ref == False:
                self.inter_company_transfer = trans_cls.create({
                    'sale_id': self.id,
                    'invoice_id': [(6, 0, self.invoice_ids.ids)],
                    'state': 'process',
                    'apply_type': 'purchase',
                    'from_warehouse': self.warehouse_id.id,
                    'pricelist_id': self.pricelist_id.id,
                })
            else:
                self.inter_company_transfer.write({
                    'sale_id': self.id or False,
                    'pricelist_id': self.pricelist_id.id or False,
                })
                if not self.inter_company_transfer.from_warehouse.id:
                    self.inter_company_transfer.write({'from_warehouse': self.warehouse_id.id})
                if self.invoice_ids:
                    self.inter_company_transfer.write({'invoice_id': [(6, 0, self.invoice_ids.ids)]})

            for inter_line in inter_lines:
                inter_line.update({'inter_company_transfer': self.inter_company_transfer.id})

            if self.client_order_ref == False:
                self._create_purchase_order_from_sale_order()
        return res
