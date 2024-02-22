from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class InterTransferCompanyLines(models.Model):
    _name = 'inter.transfer.company.line'
    _description = "InterTransferCompanyLines"

    inter_transfer_id = fields.Many2one('inter.transfer.company')
    product_id = fields.Many2one('product.product', required=True)
    quantity = fields.Integer('Quantity', default=1, required=True)
    price_unit = fields.Float('Price')

    def _prepare_internal_from_move_line(self, move):
        return ({
            'product_id': move.product_id.id,
            'quantity': move.product_uom_qty,
            'price_unit': move.sale_line_id.price_unit or move.product_id.lst_price
        })

    @api.onchange('product_id')
    def _onchange_product(self):
        for rec in self:
            if rec.product_id:
                rec.write({'price_unit': rec.product_id.list_price})


class InterTransferCompany(models.Model):
    _name = 'inter.transfer.company'
    _description = "InterTransferCompany"
    _order = 'create_date desc, id desc'

    name = fields.Char("Name", readonly=True, copy=False)
    sale_id = fields.Many2one("sale.order", string="Sale Order", copy=False)
    invoice_id = fields.Many2many("account.move", string='Invoice', related="sale_id.invoice_ids", copy=False)
    purchase_id = fields.Many2one("purchase.order", string="Purchase Order", copy=False)
    bill_id = fields.Many2many("account.move", string='Bills', related="purchase_id.invoice_ids", copy=False)
    return_id = fields.Many2one("return.inter.transfer.company", string='return', copy=False)
    state = fields.Selection([('draft', 'Draft'), ('process', 'Process'), ('return', 'Return')], string="state",
                             default='draft', readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency")
    from_warehouse = fields.Many2one('stock.warehouse', string="From Warehouse",
                                     domain=lambda self: [('company_id', '=', self.env.company.id)])
    to_warehouse = fields.Many2one('stock.warehouse', string="To Warehouse",
                                   domain=lambda self: [('company_id', '!=', self.env.company.id)])
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")
    apply_type = fields.Selection([('sale', 'Sale Order'), ('purchase', 'Purchase Order'),
                                   ('sale_purchase', 'Sale and Purchase Order')], default="sale_purchase",
                                  string="Apply Type")
    product_lines = fields.One2many('inter.transfer.company.line', 'inter_transfer_id', string="lines")

    def action_view_internal(self):
        return {
            'name': _('Internal Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'inter.transfer.company',
            'view_mode': 'form',
            'view_id': self.env.ref('bi_inter_company_transfer.view_inter_company_transfer_form').id,
            'res_id': self.id,
        }

    def action_view_return_internal(self):
        return self.return_id.action_view_internal()

    def action_view_sale_internal(self):
        return {
            'name': _('Sale Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_id.id,
            'view_id': self.env.ref('sale.view_order_form').id,
            'target': 'current',
        }

    def action_view_invoice_internal(self):
        return self.sale_id.action_view_invoice(self.invoice_id)

    def action_view_bill_internal(self):
        return self.purchase_id.action_view_invoice(self.bill_id)

    def action_view_purchase_internal(self):
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_id.id,
            'view_id': self.env.ref('purchase.purchase_order_form').id,
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('inter.transfer.company')
        return super(InterTransferCompany, self).create(vals)

    @api.onchange('from_warehouse')
    def change_details(self):
        if self.from_warehouse:
            from_partner = self.from_warehouse.company_id.partner_id
            self.currency_id = from_partner.currency_id.id
            self.pricelist_id = from_partner.property_product_pricelist.id

    def action_view_return_form(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        value = [{
            'product_id': i.product_id.id,
            'quantity': i.quantity,
            'price_unit': i.price_unit
        } for i in self.product_lines]

        return {
            'name': _('Return'),
            'type': 'ir.actions.actions',
            'res_model': 'return.inter.transfer.company',
            'view_mode': 'form',
            'view_id': self.env.ref('bi_inter_company_transfer.action_return_form_template').id,
            'target': 'new',
            'context': {
                'default_inter_transfer_id': self.id,
                'default_from_warehouse': self.from_warehouse.id,
                'default_to_warehouse': self.to_warehouse.id,
                'default_pricelist_id': self.pricelist_id.id,
                'default_currency_id': self.currency_id.id,
                'default_sale_id': self.sale_id.id,
                'default_purchase_id': self.purchase_id.id,
                'default_product_lines': value
            },
        }
