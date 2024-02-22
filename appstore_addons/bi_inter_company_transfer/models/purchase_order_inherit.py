from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    inter_transfer_id = fields.Many2one('inter.transfer.company', copy=False)
    inter_transfer_count = fields.Integer(string="Internal Transfer", compute="_compute_intertransfer_count",
                                          copy=False, default=0, store=True)

    @api.depends('inter_transfer_id')
    def _compute_intertransfer_count(self):
        for record in self:
            record.inter_transfer_count = len(self.inter_transfer_id)

    def action_view_internal(self):
        return self.inter_transfer_id.action_view_internal()

    @api.model
    def get_so_line_data(self, company, sale_id, line):
        fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
        taxes = line.product_id.taxes_id.filtered(lambda r: not line.company_id or r.company_id == company)
        tax_ids = fpos.map_tax(taxes) if fpos else taxes
        quantity = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)

        price = line.price_unit or 0.0
        price = line.product_uom._compute_price(price, line.product_id.uom_id)
        return {
            'name': line.name,
            'customer_lead': line.product_id and line.product_id.sale_delay or 0.0,
            'tax_id': [(6, 0, tax_ids.ids)],
            'order_id': sale_id,
            'product_uom_qty': quantity,
            'product_id': line.product_id and line.product_id.id or False,
            'product_uom': line.product_id and line.product_id.uom_id.id or line.product_uom.id,
            'price_unit': price,
            'company_id': company.id
        }

    def get_so_values(self, name, company_partner_id, partner_id):
        if company_partner_id:
            if not company_partner_id.intercompany_warehouse_id:
                raise ValidationError(_('Please select intercompany warehouse on  %s.') % company_partner_id.name)

        so_name = self.env['ir.sequence'].sudo().with_company(company_partner_id).next_by_code('sale.order') or '/'
        if self.inter_transfer_id.id and self.inter_transfer_id.pricelist_id.id:
            pricelist_id = self.inter_transfer_id.pricelist_id.id
        else:
            pricelist_id = partner_id.property_product_pricelist.id
        return {
            'name': so_name,
            'partner_invoice_id': partner_id.id,
            'date_order': self.date_order,
            'fiscal_position_id': partner_id.property_account_position_id.id,
            'payment_term_id': partner_id.property_payment_term_id.id,
            'user_id': False,
            'company_id': company_partner_id.id,
            'warehouse_id': company_partner_id.intercompany_warehouse_id.id,
            'client_order_ref': name,
            'partner_id': partner_id.id,
            'pricelist_id': pricelist_id,
            'inter_transfer_id': self.inter_transfer_id.id,
            'partner_shipping_id': partner_id.id
        }

    def _create_so_from_po(self):
        company_partner_id = self.env['res.company'].search([('partner_id', '=', self.partner_id.id)])
        sale_order = self.env['sale.order']
        invoice = False
        sale_order_line = self.env['sale.order.line']
        allowed_company_ids = [company_partner_id.id, self.env.company.id]
        so_vals = self.sudo().get_so_values(self.name, company_partner_id,
                                            self.env.company.intercompany_warehouse_id.partner_id)
        so_id = sale_order.with_context(allowed_company_ids=allowed_company_ids).sudo().create(so_vals)
        for line in self.order_line.sudo():
            so_line_vals = self.sudo().get_so_line_data(company_partner_id, so_id.id, line)
            sale_order_line.with_context(allowed_company_ids=allowed_company_ids).sudo().create(so_line_vals)
        if so_id.client_order_ref:
            so_id.client_order_ref = self.name
        ctx = dict(self._context or {})
        ctx.update({'company_partner_id': company_partner_id.id, 'current_company_id': self.env.company.id})
        so_id.with_context(allowed_company_ids=allowed_company_ids).action_confirm()

        if self.env.company.validate_picking:
            for picking in so_id.picking_ids:
                if picking.state != 'done':
                    for move in picking.move_ids_without_package:
                        if move.product_id.qty_available > 0:
                            move.write({
                                'quantity': move.product_uom_qty,
                            })
                    picking.button_validate()
                    picking._action_done()
        if self.env.company.create_invoice:
            invoice = so_id.order_line.invoice_lines.move_id.filtered(lambda r: r.move_type in
                                                                      ('out_invoice', 'out_refund'))
            if not invoice:
                invoice = so_id.sudo()._create_invoices()

            if self.env.company.validate_invoice:
                if invoice.state != 'posted':
                    invoice_id = self.env['account.move'].browse(invoice.id)
                    invoice_id.sudo()._post()
                else:
                    invoice_id = invoice

        if self.inter_transfer_id.id:
            if self.env.company.validate_invoice:
                bill_details = []
                bill_details.append(invoice_id.id)
                if len(self.inter_transfer_id.invoice_id) > 0:
                    for inv in self.inter_transfer_id.invoice_id:
                        bill_details.append(inv.id)
            if not self.inter_transfer_id.to_warehouse.id:
                self.inter_transfer_id.update({
                    'sale_id': so_id.id,
                    'pricelist_id': so_id.pricelist_id.id,
                    'from_warehouse': so_id.warehouse_id.id,
                    'to_warehouse': self.env.company.intercompany_warehouse_id.id
                })
            else:
                self.inter_transfer_id.update({
                    'sale_id': so_id.id,
                    'pricelist_id': so_id.pricelist_id.id,
                    'from_warehouse': so_id.warehouse_id.id,
                })

            so_id.inter_transfer_id = self.inter_transfer_id.id
        return so_id

    def button_confirm(self):
        res = super(PurchaseOrderInherit, self).button_confirm()
        company_partner_id = self.env['res.company'].search([('partner_id', '=', self.partner_id.id)])
        if not company_partner_id.id:
            return res
        so_available = self.env['sale.order'].search([('client_order_ref', '=', self.name)])
        setting_id = self.env.company
        invoice_object = self.env['account.move']
        journal = self.env['account.journal'].sudo().search([('type', '=', 'purchase'),
                                                             ('company_id', '=', self.env.company.id)], limit=1)
        inter_transfer_id = self.env['inter.transfer.company']
        inter_transfer_lines = self.env['inter.transfer.company.line']
        inter_lines = []
        bill_id = False
        line_lot = []
        if self.env.user.has_group(
                'bi_inter_company_transfer.group_ict_manager_access') and setting_id.allow_auto_intercompany:
            if not so_available.id:
                if setting_id.validate_picking:
                    for line in self.order_line:
                        if line.product_id.tracking != 'none':
                            line_lot.append(line.product_id)
                    for receipt in self.picking_ids:
                        for move in receipt.move_ids_without_package:
                            move.write({'quantity': move.product_uom_qty})
                            if self.inter_transfer_id.id == False and self.partner_ref == False:
                                data = inter_transfer_lines.create({
                                    'product_id': move.product_id.id,
                                    'quantity': move.product_uom_qty,
                                    'price_unit': move.purchase_line_id.price_unit
                                })
                                inter_lines.append(data)
                        if not line_lot:
                            receipt._action_done()
                        else:
                            receipt.action_confirm()
                        for move in receipt.move_ids_without_package:
                            if move.account_move_ids:
                                for entry in move.account_move_ids:
                                    entry.write({'partner_id': move.partner_id.id})

                else:
                    for receipt in self.picking_ids:
                        for move in receipt.move_ids_without_package:
                            if self.inter_transfer_id.id == False and self.partner_ref == False:
                                data = inter_transfer_lines.create({
                                    'product_id': move.product_id.id,
                                    'quantity': move.product_uom_qty,
                                    'price_unit': move.product_id.lst_price
                                })
                                inter_lines.append(data)
                if setting_id.create_invoice:
                    ctx = dict(self._context or {})
                    ctx.update({
                        'move_type': 'in_invoice',
                        'default_purchase_id': self.id,
                        'default_currency_id': self.currency_id.id,
                        'default_invoice_origin': self.name,
                        'default_ref': self.name,
                    })
                    bill_id = invoice_object.with_context(ctx).create({
                        'partner_id': self.partner_id.id,
                        'currency_id': self.currency_id.id,
                        'company_id': self.company_id.id,
                        'move_type': 'in_invoice',
                        'journal_id': journal.id,
                        'purchase_vendor_bill_id': self.id,
                        'purchase_id': self.id,
                        'ref': self.name
                    })
                    new_lines = self.env['account.move.line']
                    new_lines = []
                    for line in self.order_line.filtered(lambda l: not l.display_type):
                        new_lines.append((0, 0, line._prepare_account_move_line(bill_id)))
                    bill_id.write({'invoice_line_ids': new_lines, 'purchase_id': False, 'invoice_date': bill_id.date})
                    bill_id.invoice_payment_term_id = self.payment_term_id
                    bill_id.invoice_origin = ', '.join(self.mapped('name'))
                    bill_id.ref = ', '.join(self.filtered('partner_ref').mapped('partner_ref')) or bill_id.ref

                    if setting_id.validate_invoice:
                        bill_id._post()
                if self.inter_transfer_id.id == False and self.partner_ref == False:
                    internal_transfer_vals = {
                        'purchase_id': self.id,
                        'state': 'process',
                        'apply_type': 'sale',
                        'currency_id': self.currency_id.id,
                        'to_warehouse': self.picking_type_id.warehouse_id.id
                    }
                    if bill_id:
                        internal_transfer_vals['invoice_id'] = [(6, 0, bill_id.ids)]

                    internal_transfer_id = inter_transfer_id.create(internal_transfer_vals)
                    self.inter_transfer_id = internal_transfer_id.id
                    for inter_transfer_company_line_id in inter_lines:
                        inter_transfer_company_line_id.update({'inter_transfer_id': self.inter_transfer_id.id})
                else:
                    created_id = inter_transfer_id.search([('id', '=', self.inter_transfer_id.id)])
                    created_id.write({'purchase_id': self.id})
                    if bill_id:
                        created_id.write({'invoice_id': [(6, 0, bill_id.ids)]})
                if self.inter_transfer_id.id:
                    self.inter_transfer_id = self.inter_transfer_id.id

                if self._context.get('stop_so') == True:
                    pass
                else:
                    receipt = self._create_so_from_po()
        return res
