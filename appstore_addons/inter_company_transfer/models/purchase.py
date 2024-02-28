from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def create_from_sale_order_line(self, line, purchase_order, partner_company):
        return self.sudo().create({
            'order_id': purchase_order.id,
            'name': line.name,
            'date_planned': line.order_id.expected_date,
            'product_qty': line.product_uom_qty,
            'product_id': line.product_id.id,
            'product_uom': line.product_uom.id,
            'price_unit': line.price_unit,
            'taxes_id': line.tax_id.map_tax_ids(partner_company).ids,
        })


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    inter_company_transfer = fields.Many2one('inter.company.transfer', copy=False)

    def action_view_internal(self):
        return self.inter_company_transfer.action_view_internal()

    @api.model
    def create_from_sale_order(self, sale_order, partner_company, current_company):
        currency_id = sale_order.inter_company_transfer.currency_id.id if sale_order.inter_company_transfer.id and sale_order.inter_company_transfer.currency_id.id else sale_order.currency_id.id
        vals = {
            'name': self.env['ir.sequence'].sudo().with_company(partner_company).next_by_code('purchase.order'),
            'origin': sale_order.name,
            'fiscal_position_id': current_company.partner_id.property_account_position_id.id,
            'payment_term_id': current_company.partner_id.property_supplier_payment_term_id.id,
            'partner_ref': sale_order.name,
            'currency_id': currency_id,
            'user_id': sale_order.env.uid,
            'partner_id': current_company.partner_id.id,
            'inter_company_transfer': sale_order.inter_company_transfer.id,
            'date_order': sale_order.date_order,
            'company_id': partner_company.id,
        }
        purchase_order = self.sudo().create(vals)
        for order_line in sale_order.order_line:
            self.env['purchase.order.line'].sudo().create_from_sale_order_line(order_line, purchase_order,
                                                                               partner_company)
        return purchase_order

    def _create_sale_order_from_purchase_order(self):
        partner_company = self.env['res.company'].search([('partner_id', '=', self.partner_id.id)])
        allowed_company_ids = [partner_company.id, self.env.company.id]
        sale_order = self.env['sale.order'].sudo().create_from_purchase_order(
            self, partner_company, self.env.company.intercompany_warehouse_id.partner_id, allowed_company_ids)
        if sale_order.client_order_ref:
            sale_order.client_order_ref = self.name
        sale_order.with_context(allowed_company_ids=allowed_company_ids).action_confirm()

        if self.env.company.validate_picking:
            for picking in sale_order.picking_ids.filtered(lambda picking: picking.state != 'done'):
                for move in picking.move_ids_without_package.filtered(lambda move: move.product_id.qty_available > 0):
                    move.write({'quantity': move.product_uom_qty})
                picking.button_validate()
                picking._action_done()

        if self.env.company.create_invoice:
            invoice = sale_order.order_line.invoice_lines.move_id.filtered(lambda r: r.move_type in
                                                                           ('out_invoice', 'out_refund'))
            if not invoice:
                invoice = sale_order.sudo()._create_invoices()

            if self.env.company.validate_invoice and invoice.state != 'posted':
                invoice.sudo()._post()

        if self.inter_company_transfer.id:
            self.inter_company_transfer.update({
                'sale_id': sale_order.id,
                'pricelist_id': sale_order.pricelist_id.id,
                'from_warehouse': sale_order.warehouse_id.id,
            })
            if not self.inter_company_transfer.to_warehouse.id:
                self.inter_company_transfer.update({'to_warehouse': self.env.company.intercompany_warehouse_id.id})
            sale_order.inter_company_transfer = self.inter_company_transfer.id
        return sale_order

    def create_bill_int(self, company, is_sale_bill: bool = False):
        journal = self.env['account.journal'].sudo().search([('type', '=', 'purchase'),
                                                             ('company_id', '=', company.id)], limit=1)
        if not journal:
            raise ValidationError(_(f'Please define purchase journal for company: {company.name}.'))

        for purchase_order_line_id in self.order_line:
            purchase_order_line_id.qty_to_invoice = purchase_order_line_id.product_qty

        if is_sale_bill:
            account_move = self.env['account.move'].with_context(create_bill=True).sudo().with_company(company)
        else:
            account_move = self.env['account.move']
        bill = account_move.create({
            'purchase_id': self.id,
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'move_type': 'in_invoice',
            'journal_id': journal.id,
            'purchase_vendor_bill_id': self.id,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_origin': self.name,
            'ref': self.name
        })

        lines = [(0, 0, line._prepare_account_move_line(bill)) for line in self.order_line if not line.display_type]
        bill.write({'invoice_line_ids': lines, 'purchase_id': False, 'invoice_date': bill.date})
        bill.ref = ', '.join(self.filtered('partner_ref').mapped('partner_ref')) or bill.ref
        return bill

    def _create_inter_lines(self, picking) -> list:
        line_cls = self.env['inter.company.transfer.line']
        inter_lines = []
        for move in picking.move_ids_without_package:
            if self.inter_company_transfer.id == False and self.partner_ref == False:
                price = move.purchase_line_id.price_unit if self.env.company.validate_picking else move.product_id.lst_price

                if self.env.company.validate_picking is True:
                    move.write({'quantity': move.product_uom_qty})

                inter_lines.append(
                    line_cls.create({
                        'product_id': move.product_id.id,
                        'quantity': move.product_uom_qty,
                        'price_unit': price
                    }))

            if self.env.company.validate_picking is True:
                if self.order_line.filtered(lambda l: l.product_id.tracking == 'none'):
                    picking._action_done()
                else:
                    picking.action_confirm()
                for move in picking.move_ids_without_package:
                    for entry in move.account_move_ids:
                        entry.write({'partner_id': move.partner_id.id})
        return inter_lines

    def _create_inter_company_purchase(self) -> None:
        trans_cls = self.env['inter.company.transfer']

        inter_lines = [line for picking in self.picking_ids for line in self._create_inter_lines(picking)]

        if self.env.company.create_invoice is True:
            bill_id = self.create_bill_int(self.env.company)
            if self.env.company.validate_invoice is True:
                bill_id._post()

        if self.inter_company_transfer.id == False and self.partner_ref == False:
            self.inter_company_transfer = trans_cls.create({
                'state': 'process',
                'apply_type': 'sale',
                'currency_id': self.currency_id.id,
            })

        self.inter_company_transfer.update({
            'purchase_id': self.id,
            'to_warehouse': self.picking_type_id.warehouse_id.id,
        })

        for inter_line in inter_lines:
            inter_line.update({'inter_company_transfer': self.inter_company_transfer.id})

        if self.env.company.create_invoice:
            self.inter_company_transfer.write({'invoice_id': [(6, 0, bill_id.ids)]})

        self._create_sale_order_from_purchase_order()

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        partner_company = self.env['res.company'].search([('partner_id', '=', self.partner_id.id)])
        is_correct_group = self.env.user.has_group('inter_company_transfer.group_ict_manager_access')
        if partner_company.id and is_correct_group and self.env.company.allow_intercompany_transactions:
            if not self.env['sale.order'].search([('client_order_ref', '=', self.name)]).id:
                self._create_inter_company_purchase()
        return res
