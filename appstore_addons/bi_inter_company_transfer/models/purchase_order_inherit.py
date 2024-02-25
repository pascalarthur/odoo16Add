from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def create_from_sale_order_line(self, line, purchase_order, company):
        fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
        taxes = line.product_id.taxes_id.filtered(lambda r: not line.company_id or r.company_id == company)
        tax_ids = fpos.map_tax(taxes) if fpos else taxes
        price = line.price_unit - (line.price_unit * (line.discount / 100))
        quantity = line.product_uom._compute_quantity(line.product_uom_qty,
                                                      line.product_id.uom_po_id) or line.product_uom_qty
        price = line.product_uom._compute_price(price, line.product_id.uom_po_id) or price
        return self.sudo().create({
            'name': line.name,
            'date_planned': line.order_id.expected_date,
            'taxes_id': [(6, 0, tax_ids.ids)],
            'order_id': purchase_order.id,
            'product_qty': quantity,
            'product_id': line.product_id and line.product_id.id or False,
            'product_uom': line.product_id and line.product_id.uom_po_id.id or line.product_uom.id,
            'price_unit': price or 0.0,
        })


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    inter_transfer_id = fields.Many2one('inter.transfer.company', copy=False)

    def action_view_internal(self):
        return self.inter_transfer_id.action_view_internal()

    @api.model
    def create_from_sale_order(self, sale_order, company_partner, current_company):
        currency_id = sale_order.inter_transfer_id.currency_id.id if sale_order.inter_transfer_id.id and sale_order.inter_transfer_id.currency_id.id else sale_order.currency_id.id
        vals = {
            'name': self.env['ir.sequence'].sudo().with_company(company_partner).next_by_code('purchase.order'),
            'origin': sale_order.name,
            'fiscal_position_id': current_company.partner_id.property_account_position_id.id,
            'payment_term_id': current_company.partner_id.property_supplier_payment_term_id.id,
            'partner_ref': sale_order.name,
            'currency_id': currency_id,
            'user_id': sale_order.env.uid,
            'partner_id': current_company.partner_id.id,
            'inter_transfer_id': sale_order.inter_transfer_id.id,
            'date_order': sale_order.date_order,
            'company_id': company_partner.id,
        }
        purchase_order = self.sudo().create(vals)
        for order_line in sale_order.order_line:
            self.env['purchase.order.line'].sudo().create_from_sale_order_line(order_line, purchase_order,
                                                                               company_partner)
        return purchase_order

    def _create_sale_order_from_purchase_order(self):
        company_partner = self.env['res.company'].search([('partner_id', '=', self.partner_id.id)])
        allowed_company_ids = [company_partner.id, self.env.company.id]
        sale_order = self.env['sale.order'].sudo().create_from_purchase_order(
            self, company_partner, self.env.company.intercompany_warehouse_id.partner_id, allowed_company_ids)
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

        if self.inter_transfer_id.id:
            self.inter_transfer_id.update({
                'sale_id': sale_order.id,
                'pricelist_id': sale_order.pricelist_id.id,
                'from_warehouse': sale_order.warehouse_id.id,
            })
            if not self.inter_transfer_id.to_warehouse.id:
                self.inter_transfer_id.update({'to_warehouse': self.env.company.intercompany_warehouse_id.id})
            sale_order.inter_transfer_id = self.inter_transfer_id.id
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
            context = dict(self._context or {})
            context.update({
                'move_type': 'in_invoice',
                'default_purchase_id': self.id,
                'default_currency_id': self.currency_id.id,
                'default_invoice_origin': self.name,
                'default_ref': self.name,
            })
            account_move = self.env['account.move'].with_context(context)
        bill_id = account_move.create({
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'move_type': 'in_invoice',
            'journal_id': journal.id,
            'purchase_vendor_bill_id': self.id,
            'purchase_id': self.id,
            'ref': self.name
        })

        new_lines = []
        for line in self.order_line.filtered(lambda l: not l.display_type):
            new_lines.append((0, 0, line._prepare_account_move_line(bill_id)))
        bill_id.write({'invoice_line_ids': new_lines, 'purchase_id': False, 'invoice_date': bill_id.date})
        bill_id.invoice_payment_term_id = self.payment_term_id
        bill_id.invoice_origin = ', '.join(self.mapped('name'))
        bill_id.ref = ', '.join(self.filtered('partner_ref').mapped('partner_ref')) or bill_id.ref
        return bill_id

    def _create_inter_lines(self, picking) -> list:
        line_cls = self.env['inter.transfer.company.line']
        inter_lines = []
        for move in picking.move_ids_without_package:
            if self.inter_transfer_id.id == False and self.partner_ref == False:
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
        trans_cls = self.env['inter.transfer.company']

        inter_lines = [line for picking in self.picking_ids for line in self._create_inter_lines(picking)]

        if self.env.company.create_invoice is True:
            bill_id = self.create_bill_int(self.env.company)
            if self.env.company.validate_invoice is True:
                bill_id._post()

        if self.inter_transfer_id.id == False and self.partner_ref == False:
            self.inter_transfer_id = trans_cls.create({
                'purchase_id': self.id,
                'state': 'process',
                'apply_type': 'sale',
                'currency_id': self.currency_id.id,
                'to_warehouse': self.picking_type_id.warehouse_id.id
            })
        else:
            self.inter_transfer_id.write({'purchase_id': self.id})

        for inter_line in inter_lines:
            inter_line.update({'inter_transfer_id': self.inter_transfer_id.id})

        if self.env.company.create_invoice:
            self.inter_transfer_id.write({'invoice_id': [(6, 0, bill_id.ids)]})

        if self._context.get('stop_so') != True:
            self._create_sale_order_from_purchase_order()

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        company_partner = self.env['res.company'].search([('partner_id', '=', self.partner_id.id)])
        is_correct_group = self.env.user.has_group('bi_inter_company_transfer.group_ict_manager_access')
        if company_partner.id and is_correct_group and self.env.company.allow_auto_intercompany:
            if not self.env['sale.order'].search([('client_order_ref', '=', self.name)]).id:
                self._create_inter_company_purchase()
        return res
