from odoo import api, fields, models, _


class InterTransferCompanyLines(models.Model):
    _name = 'inter.transfer.company.line'
    _description = "InterTransferCompanyLines"

    inter_transfer_id = fields.Many2one('inter.transfer.company')
    product_id = fields.Many2one('product.product', required=True)
    quantity = fields.Integer('Quantity', default=1, required=True)
    price_unit = fields.Float('Price')

    @api.model
    def create_from_move(self, move):
        return self.create({
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
    _description = "Intercompany Transfer"
    _order = 'create_date desc, id desc'

    name = fields.Char("Name", readonly=True, copy=False)
    sale_id = fields.Many2one("sale.order", string="Sale Order", copy=False)
    invoice_id = fields.Many2many("account.move", string='Invoice', related="sale_id.invoice_ids", copy=False)
    purchase_id = fields.Many2one("purchase.order", string="Purchase Order", copy=False)
    bill_id = fields.Many2many("account.move", string='Bills', related="purchase_id.invoice_ids", copy=False)
    state = fields.Selection([('draft', 'Draft'), ('process', 'Process'), ('return', 'Return')], string="State",
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

    inter_company_transfer_id = fields.Many2one("inter.transfer.company", string='Inter Company Transfer', copy=False)
    inter_company_transfer_return_id = fields.Many2one("inter.transfer.company", string='Return', copy=False)
    is_return = fields.Boolean('Is Return', compute='_compute_is_return', default=False, store=True)

    @api.depends('inter_company_transfer_return_id')
    def _compute_is_return(self):
        for rec in self:
            rec.is_return = bool(rec.inter_company_transfer_id)

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
        if self.inter_company_transfer_return_id:
            return self.inter_company_transfer_return_id.action_view_internal()
        else:
            return self.inter_company_transfer_id.action_view_internal()

    def action_view_invoice_internal(self):
        return self.sale_id.action_view_invoice(self.invoice_id)

    def action_view_bill_internal(self):
        return self.purchase_id.action_view_invoice(self.bill_id)

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

    def process_return(self, sale_order):
        '''
        Find sale order and create inverse purchase -> Purchase order, Invoice and Bill are then automatically created
        '''
        self.inter_company_transfer_id.write({'state': 'return'})

        self.purchase_id = self.env['purchase.order'].create({
            'partner_id': sale_order.partner_id.id,
            'company_id': sale_order.company_id.id,
            'currency_id': sale_order.currency_id.id,
            'inter_transfer_id': self.id
        })
        for line in sale_order.order_line:
            self.env['purchase.order.line'].create({
                'order_id': self.purchase_id.id,
                'product_id': line.product_id.id,
                'product_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
                'taxes_id': [(6, 0, line.tax_id.ids)],
            })
        self.purchase_id.button_confirm()

    @api.model
    def create(self, vals):
        if 'inter_company_transfer_id' in vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('return.inter.transfer.company')

            res = super(InterTransferCompany, self).create(vals)

            sale_order = self.env['inter.transfer.company'].browse(vals['inter_company_transfer_id']).sale_id
            res.process_return(sale_order)

            if 'inter_company_transfer_id' in vals:
                inter_transfer = self.env['inter.transfer.company'].search([('id', '=',
                                                                             vals['inter_company_transfer_id'])])
                inter_transfer.write({'inter_company_transfer_return_id': res.id})
            return res
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('inter.transfer.company')
            return super(InterTransferCompany, self).create(vals)

    @api.onchange('from_warehouse')
    def change_details(self):
        for rec in self:
            from_partner = rec.from_warehouse.company_id.partner_id
            rec.currency_id = from_partner.currency_id.id
            rec.pricelist_id = from_partner.property_product_pricelist.id

    def action_view_return_form(self):
        value = [{
            'product_id': i.product_id.id,
            'quantity': i.quantity,
            'price_unit': i.price_unit
        } for i in self.product_lines]

        return {
            'name': _('Return'),
            'type': 'ir.actions.act_window',
            'res_model': 'inter.transfer.company',
            'view_mode': 'form',
            'view_id': self.env.ref('bi_inter_company_transfer.view_inter_company_transfer_form').id,
            'target': 'new',
            'context': {
                'default_inter_company_transfer_id': self.id,
                'default_from_warehouse': self.to_warehouse.id,
                'default_to_warehouse': self.from_warehouse.id,
                'default_pricelist_id': self.pricelist_id.id,
                'default_currency_id': self.currency_id.id,
                'default_product_lines': value,
            },
        }
