# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from functools import lru_cache
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class account_invoice_line(models.Model):
    _inherit = 'account.move.line'

    @api.depends('product_id', 'product_uom_id')
    def _compute_price_unit(self):
        for line in self:
            manual_currency_rate_active = line.move_id.manual_currency_rate_active
            manual_currency_rate = line.move_id.manual_currency_rate
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            if line.move_id.is_sale_document(include_receipts=True):
                document_type = 'sale'
            elif line.move_id.is_purchase_document(include_receipts=True):
                document_type = 'purchase'
            else:
                document_type = 'other'

            line.price_unit = line.product_id.with_context(manual_currency_rate_active=manual_currency_rate_active,manual_currency_rate=manual_currency_rate)._get_tax_included_unit_price(
                line.move_id.company_id,
                line.move_id.currency_id,
                line.move_id.date,
                document_type,
                fiscal_position=line.move_id.fiscal_position_id,
                product_uom=line.product_uom_id,
            )

    @api.depends('currency_id', 'company_id', 'move_id.date', 
        'move_id.manual_currency_rate_active', 'move_id.manual_currency_rate')
    def _compute_currency_rate(self):
        @lru_cache()
        def get_rate(from_currency, to_currency, company, date):
            return self.env['res.currency']._get_conversion_rate(
                from_currency=from_currency,
                to_currency=to_currency,
                company=company,
                date=date,
            )
        for line in self:
            if line.move_id.manual_currency_rate_active:
                line.currency_rate = line.move_id.manual_currency_rate or 1.0
            else:
                line.currency_rate = get_rate(
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.move_id.date or fields.Date.context_today(line),
                )

    
    @api.model
    def _prepare_reconciliation_single_partial(self, debit_values, credit_values, shadowed_aml_values=None):
        """ Prepare the values to create an account.partial.reconcile later when reconciling the dictionaries passed
        as parameters, each one representing an account.move.line.
        :param debit_values:  The values of account.move.line to consider for a debit line.
        :param credit_values: The values of account.move.line to consider for a credit line.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        :return: A dictionary:
            * debit_values:     None if the line has nothing left to reconcile.
            * credit_values:    None if the line has nothing left to reconcile.
            * partial_values:   The newly computed values for the partial.
            * exchange_values:  The values to create an exchange difference linked to this partial.
        """
        # ==== Determine the currency in which the reconciliation will be done ====
        # In this part, we retrieve the residual amounts, check if they are zero or not and determine in which
        # currency and at which rate the reconciliation will be done.

        def get_odoo_rate(vals):
            if vals.get('manual_currency_rate'):
                exchange_rate = vals.get('manual_currency_rate')
                return exchange_rate

        res = {
            'debit_values': debit_values,
            'credit_values': credit_values,
        }
        
        if debit_values.get('record') and debit_values['record'].move_id.manual_currency_rate_active and debit_values['record'].move_id.manual_currency_rate:
            debit_values['manual_currency_rate'] = debit_values['record'].move_id.manual_currency_rate
        if credit_values.get('record') and credit_values['record'].move_id.manual_currency_rate_active and credit_values['record'].move_id.manual_currency_rate:
            credit_values['manual_currency_rate'] = credit_values['record'].move_id.manual_currency_rate
        

        debit_aml = debit_values['aml']
        credit_aml = credit_values['aml']
        debit_currency = debit_aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
        credit_currency = credit_aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
        company_currency = debit_aml.company_currency_id

        remaining_debit_amount_curr = debit_values['amount_residual_currency']
        remaining_credit_amount_curr = credit_values['amount_residual_currency']
        remaining_debit_amount = debit_values['amount_residual']
        remaining_credit_amount = credit_values['amount_residual']

        debit_available_residual_amounts = self._prepare_move_line_residual_amounts(
            debit_values,
            credit_currency,
            shadowed_aml_values=shadowed_aml_values,
            other_aml_values=credit_values,
        )
        credit_available_residual_amounts = self._prepare_move_line_residual_amounts(
            credit_values,
            debit_currency,
            shadowed_aml_values=shadowed_aml_values,
            other_aml_values=debit_values,
        )

        if debit_currency != company_currency \
            and debit_currency in debit_available_residual_amounts \
            and debit_currency in credit_available_residual_amounts:
            recon_currency = debit_currency
        elif credit_currency != company_currency \
            and credit_currency in debit_available_residual_amounts \
            and credit_currency in credit_available_residual_amounts:
            recon_currency = credit_currency
        else:
            recon_currency = company_currency

        debit_recon_values = debit_available_residual_amounts.get(recon_currency)
        credit_recon_values = credit_available_residual_amounts.get(recon_currency)

        # Check if there is something left to reconcile. Move to the next loop iteration if not.
        skip_reconciliation = False
        if not debit_recon_values:
            res['debit_values'] = None
            skip_reconciliation = True
        if not credit_recon_values:
            res['credit_values'] = None
            skip_reconciliation = True
        if skip_reconciliation:
            return res

        recon_debit_amount = debit_recon_values['residual']
        recon_credit_amount = -credit_recon_values['residual']

        # ==== Match both lines together and compute amounts to reconcile ====

        # Special case for exchange difference lines. In that case, both lines are sharing the same foreign
        # currency but at least one has no amount in foreign currency.
        # In that case, we don't want a rate for the opposite line because the exchange difference is supposed
        # to reduce only the amount in company currency but not the foreign one.
        exchange_line_mode = \
            recon_currency == company_currency \
            and debit_currency == credit_currency \
            and (
                not debit_available_residual_amounts.get(debit_currency)
                or not credit_available_residual_amounts.get(credit_currency)
            )

        # Determine which line is fully matched by the other.
        compare_amounts = recon_currency.compare_amounts(recon_debit_amount, recon_credit_amount)
        min_recon_amount = min(recon_debit_amount, recon_credit_amount)
        debit_fully_matched = compare_amounts <= 0
        credit_fully_matched = compare_amounts >= 0

        # ==== Computation of partial amounts ====
        if recon_currency == company_currency:
            if exchange_line_mode:
                debit_rate = None
                credit_rate = None
            else:
                debit_rate = debit_available_residual_amounts.get(debit_currency, {}).get('rate')
                credit_rate = credit_available_residual_amounts.get(credit_currency, {}).get('rate')

            # Compute the partial amount expressed in company currency.
            partial_amount = min_recon_amount

            # Compute the partial amount expressed in foreign currency.
            if debit_rate:
                partial_debit_amount_currency = debit_currency.round(debit_rate * min_recon_amount)
                partial_debit_amount_currency = min(partial_debit_amount_currency, remaining_debit_amount_curr)
            else:
                partial_debit_amount_currency = 0.0
            if credit_rate:
                partial_credit_amount_currency = credit_currency.round(credit_rate * min_recon_amount)
                partial_credit_amount_currency = min(partial_credit_amount_currency, -remaining_credit_amount_curr)
            else:
                partial_credit_amount_currency = 0.0

        else:
            # recon_currency != company_currency
            if exchange_line_mode:
                debit_rate = None
                credit_rate = None
            else:
                debit_rate = debit_recon_values['rate']
                credit_rate = credit_recon_values['rate']

            # Compute the partial amount expressed in foreign currency.
            if debit_rate:
                partial_debit_amount = company_currency.round(min_recon_amount / debit_rate)
                partial_debit_amount = min(partial_debit_amount, remaining_debit_amount)
            else:
                partial_debit_amount = 0.0
            if credit_rate:
                partial_credit_amount = company_currency.round(min_recon_amount / credit_rate)
                partial_credit_amount = min(partial_credit_amount, -remaining_credit_amount)
            else:
                partial_credit_amount = 0.0
            partial_amount = min(partial_debit_amount, partial_credit_amount)

            # Compute the partial amount expressed in foreign currency.
            # Take care to handle the case when a line expressed in company currency is mimicking the foreign
            # currency of the opposite line.
            if debit_currency == company_currency:
                partial_debit_amount_currency = partial_amount
            else:
                partial_debit_amount_currency = min_recon_amount
            if credit_currency == company_currency:
                partial_credit_amount_currency = partial_amount
            else:
                partial_credit_amount_currency = min_recon_amount

        # Computation of the partial exchange difference. You can skip this part using the
        # `no_exchange_difference` context key (when reconciling an exchange difference for example).
        if not self._context.get('no_exchange_difference'):
            exchange_lines_to_fix = self.env['account.move.line']
            amounts_list = []
            if recon_currency == company_currency:
                if debit_fully_matched:
                    debit_exchange_amount = remaining_debit_amount_curr - partial_debit_amount_currency
                    if not debit_currency.is_zero(debit_exchange_amount):
                        exchange_lines_to_fix += debit_aml
                        amounts_list.append({'amount_residual_currency': debit_exchange_amount})
                        remaining_debit_amount_curr -= debit_exchange_amount
                if credit_fully_matched:
                    credit_exchange_amount = remaining_credit_amount_curr + partial_credit_amount_currency
                    if not credit_currency.is_zero(credit_exchange_amount):
                        exchange_lines_to_fix += credit_aml
                        amounts_list.append({'amount_residual_currency': credit_exchange_amount})
                        remaining_credit_amount_curr += credit_exchange_amount

            else:
                if debit_fully_matched:
                    # Create an exchange difference on the remaining amount expressed in company's currency.
                    debit_exchange_amount = remaining_debit_amount - partial_amount
                    if not company_currency.is_zero(debit_exchange_amount):
                        exchange_lines_to_fix += debit_aml
                        amounts_list.append({'amount_residual': debit_exchange_amount})
                        remaining_debit_amount -= debit_exchange_amount
                        if debit_currency == company_currency:
                            remaining_debit_amount_curr -= debit_exchange_amount
                else:
                    # Create an exchange difference ensuring the rate between the residual amounts expressed in
                    # both foreign and company's currency is still consistent regarding the rate between
                    # 'amount_currency' & 'balance'.
                    debit_exchange_amount = partial_debit_amount - partial_amount
                    if company_currency.compare_amounts(debit_exchange_amount, 0.0) > 0:
                        exchange_lines_to_fix += debit_aml
                        amounts_list.append({'amount_residual': debit_exchange_amount})
                        remaining_debit_amount -= debit_exchange_amount
                        if debit_currency == company_currency:
                            remaining_debit_amount_curr -= debit_exchange_amount

                if credit_fully_matched:
                    # Create an exchange difference on the remaining amount expressed in company's currency.
                    credit_exchange_amount = remaining_credit_amount + partial_amount
                    if not company_currency.is_zero(credit_exchange_amount):
                        exchange_lines_to_fix += credit_aml
                        amounts_list.append({'amount_residual': credit_exchange_amount})
                        remaining_credit_amount -= credit_exchange_amount
                        if credit_currency == company_currency:
                            remaining_credit_amount_curr -= credit_exchange_amount
                else:
                    # Create an exchange difference ensuring the rate between the residual amounts expressed in
                    # both foreign and company's currency is still consistent regarding the rate between
                    # 'amount_currency' & 'balance'.
                    credit_exchange_amount = partial_amount - partial_credit_amount
                    if company_currency.compare_amounts(credit_exchange_amount, 0.0) < 0:
                        exchange_lines_to_fix += credit_aml
                        amounts_list.append({'amount_residual': credit_exchange_amount})
                        remaining_credit_amount += credit_exchange_amount
                        if credit_currency == company_currency:
                            remaining_credit_amount_curr += credit_exchange_amount

            if exchange_lines_to_fix:
                res['exchange_values'] = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    exchange_date=max(
                        debit_aml._get_reconciliation_aml_field_value('date', shadowed_aml_values),
                        credit_aml._get_reconciliation_aml_field_value('date', shadowed_aml_values),
                    ),
                )

        # ==== Create partials ====

        remaining_debit_amount -= partial_amount
        remaining_credit_amount += partial_amount
        remaining_debit_amount_curr -= partial_debit_amount_currency
        remaining_credit_amount_curr += partial_credit_amount_currency

        res['partial_values'] = {
            'amount': partial_amount,
            'debit_amount_currency': partial_debit_amount_currency,
            'credit_amount_currency': partial_credit_amount_currency,
            'debit_move_id': debit_aml.id,
            'credit_move_id': credit_aml.id,
        }

        debit_values['amount_residual'] = remaining_debit_amount
        debit_values['amount_residual_currency'] = remaining_debit_amount_curr
        credit_values['amount_residual'] = remaining_credit_amount
        credit_values['amount_residual_currency'] = remaining_credit_amount_curr

        if recon_currency.is_zero(recon_debit_amount) or debit_fully_matched:
            res['debit_values'] = None
        if recon_currency.is_zero(recon_credit_amount) or credit_fully_matched:
            res['credit_values'] = None

        return res



   
class account_invoice(models.Model):
    _inherit = 'account.move'

    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')
    manual_currency_rate = fields.Float('Rate', digits=(12, 6))

    @api.constrains("manual_currency_rate")
    def _check_manual_currency_rate(self):
        for record in self:
            if record.manual_currency_rate_active:
                if record.manual_currency_rate == 0:
                    raise UserError(
                        _('Exchange Rate Field is required , Please fill that.'))

    @api.onchange('manual_currency_rate_active', 'currency_id')
    def check_currency_id(self):
        if self.manual_currency_rate_active:
            if self.currency_id == self.company_id.currency_id:
                self.manual_currency_rate_active = False
                raise UserError(
                    _('Company currency and invoice currency same, You can not add manual Exchange rate for same currency.'))

    
    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            for line in self.env['account.move.line'].search(domain):

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    if move.manual_currency_rate_active and move.manual_currency_rate:
                        amount = abs(line.amount_residual) * move.manual_currency_rate
                    else:
                        amount = line.company_currency_id._convert(
                            abs(line.amount_residual),
                            move.currency_id,
                            move.company_id,
                            line.date,
                        )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency_id': move.currency_id.id,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'date': fields.Date.to_string(line.date),
                    'account_payment_id': line.payment_id.id,
                })

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = True

class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _get_tax_included_unit_price(self, company, currency, document_date, document_type,
            is_refund_document=False, product_uom=None, product_currency=None,
            product_price_unit=None, product_taxes=None, fiscal_position=None
        ):
        """ Helper to get the price unit from different models.
            This is needed to compute the same unit price in different models (sale order, account move, etc.) with same parameters.
        """

        product = self

        assert document_type

        if product_uom is None:
            product_uom = product.uom_id
        if not product_currency:
            if document_type == 'sale':
                product_currency = product.currency_id
            elif document_type == 'purchase':
                product_currency = company.currency_id
        if product_price_unit is None:
            if document_type == 'sale':
                product_price_unit = product.with_company(company).lst_price
            elif document_type == 'purchase':
                product_price_unit = product.with_company(company).standard_price
            else:
                return 0.0
        if product_taxes is None:
            if document_type == 'sale':
                product_taxes = product.taxes_id.filtered(lambda x: x.company_id == company)
            elif document_type == 'purchase':
                product_taxes = product.supplier_taxes_id.filtered(lambda x: x.company_id == company)
        # Apply unit of measure.
        if product_uom and product.uom_id != product_uom:
            product_price_unit = product.uom_id._compute_price(product_price_unit, product_uom)
        # Apply fiscal position.
        if product_taxes and fiscal_position:
            product_taxes_after_fp = fiscal_position.map_tax(product_taxes)
            flattened_taxes_after_fp = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
            flattened_taxes_before_fp = product_taxes._origin.flatten_taxes_hierarchy()
            taxes_before_included = all(tax.price_include for tax in flattened_taxes_before_fp)

            if set(product_taxes.ids) != set(product_taxes_after_fp.ids) and taxes_before_included:
                taxes_res = flattened_taxes_before_fp.compute_all(
                    product_price_unit,
                    quantity=1.0,
                    currency=currency,
                    product=product,
                    is_refund=is_refund_document,
                )
                product_price_unit = taxes_res['total_excluded']
                if any(tax.price_include for tax in flattened_taxes_after_fp):
                    taxes_res = flattened_taxes_after_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=currency,
                        product=product,
                        is_refund=is_refund_document,
                        handle_price_include=False,
                    )
                    for tax_res in taxes_res['taxes']:
                        tax = self.env['account.tax'].browse(tax_res['id'])
                        if tax.price_include:
                            product_price_unit += tax_res['amount']

        manual_currency_rate_active = self._context.get('manual_currency_rate_active')
        manual_currency_rate = self._context.get('manual_currency_rate')

        if currency != product_currency:
            if manual_currency_rate_active:
                product_price_unit = product_price_unit * manual_currency_rate
            else:
                product_price_unit = product_currency._convert(product_price_unit, currency, company, document_date)

        return product_price_unit