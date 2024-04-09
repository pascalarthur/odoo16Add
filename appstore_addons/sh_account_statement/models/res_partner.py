# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from datetime import timedelta
from datetime import datetime
from odoo.exceptions import ValidationError
import calendar
import io
import xlwt
import base64
from odoo.exceptions import UserError
import logging
import uuid

_logger = logging.getLogger(__name__)
from datetime import date,datetime
from dateutil.relativedelta import relativedelta

PAYMENT_STATE_SELECTION = [
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def default_start_date(self):
        return datetime.now().date().replace(month=1, day=1)

    @api.model
    def default_end_date(self):
        return fields.Date.today()

    start_date = fields.Date("Start Date", default=default_start_date)
    end_date = fields.Date("End Date", default=default_end_date)
    sh_date_filter = fields.Selection([
        ('this_month','This Month'),
        ('last_month','Last Month'),
        ('this_quarter','This Quarter'),
        ('last_quarter','Last Quarter'),
        ('this_year','This Year'),
        ('last_year','Last Year'),
        ('custom','Custom'),
    ])

    payment_type = fields.Selection([('fully_paid','Fully Paid'),('partial_paid','Partial Paid Or Not Paid')],string="Payment Type")
    
    sh_filter_customer_statement_ids = fields.One2many(
        "sh.res.partner.filter.statement",
        "partner_id",
        string="Customer Filtered Statements",
    )
    sh_filter_vendor_statement_ids = fields.One2many(
        "sh.vendor.filter.statement", "partner_id", string="Vendor Filtered Statements"
    )
    sh_customer_statement_ids = fields.One2many(
        "sh.customer.statement", "partner_id", string="Customer Statements"
    )
    sh_customer_zero_to_thiry = fields.Float(" 0-30")
    sh_customer_thirty_to_sixty = fields.Float(" 30-60")
    sh_customer_sixty_to_ninety = fields.Float(" 60-90")
    sh_customer_ninety_plus = fields.Float(" 90+")
    sh_customer_total = fields.Float(" Total")
    sh_vendor_statement_ids = fields.One2many(
        "sh.vendor.statement", "partner_id", string="Vendor Statements"
    )
    sh_vendor_zero_to_thiry = fields.Float("0-30")
    sh_vendor_thirty_to_sixty = fields.Float("30-60")
    sh_vendor_sixty_to_ninety = fields.Float("60-90")
    sh_vendor_ninety_plus = fields.Float("90+")
    sh_vendor_total = fields.Float("Total")
    sh_dont_send_statement_auto = fields.Boolean("Don't send statement auto ?")
    sh_dont_send_due_statement_auto = fields.Boolean(
        "Don't send Overdue statement auto ?"
    )
    sh_customer_due_statement_ids = fields.One2many(
        "sh.customer.due.statement", "partner_id", string="Customer Overdue Statements"
    )
    sh_vendor_due_statement_ids = fields.One2many(
        "sh.vendor.due.statement", "partner_id", string="Vendor Overdue Statements"
    )
    sh_compute_boolean = fields.Boolean("Boolean", compute="_compute_statements",default=True)
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    sh_cfs_statement_report_url = fields.Char(compute="_compute_cfs_report_url")
    sh_cust_statement_report_url = fields.Char(compute="_compute_cust_report_url")
    sh_cust_due_statement_report_url = fields.Char(
        compute="_compute_cust_due_report_url"
    )
    sh_vfs_statement_report_url = fields.Char(compute="_compute_vfs_report_url")
    sh_vend_statement_report_url = fields.Char(compute="_compute_vend_report_url")
    sh_vend_due_statement_report_url = fields.Char(
        compute="_compute_vend_due_report_url"
    )
    report_token = fields.Char("Access Token")
    portal_statement_url_wp = fields.Char(compute="_compute_statement_portal_url_wp")
    sh_customer_statement_config = fields.Many2many(
        "sh.statement.config",
        "res_sh_customer_statement_config",
        string="Customer Statement Config",
        readonly=True,
    )
    sh_vendor_statement_config = fields.Many2many(
        "sh.statement.config",
        "res_sh_vendor_statement_config",
        string="Vendor Statement Config",
        readonly=True,
    )
    payment_state = fields.Selection(PAYMENT_STATE_SELECTION, string="Payment Status")


    def _compute_statements(self):
        # =====================================================================
        # WRITE NEW METHOD FROM SCRACH 
        # =====================================================================
        self.ensure_one()
        company_ids=[]
        if self.env.context and self.env.context.get('allowed_company_ids'):
            company_ids=self.env.context.get('allowed_company_ids')
        elif self.env.context and self.env.context.get('uid'):
            current_user=self.env['res.users'].browse(self.env.context.get('uid'))
            if current_user:
                company_ids=current_user.company_ids.ids
        for rec in self:
            rec.sh_compute_boolean=True
            rec.sh_customer_statement_ids=[(6,0,[])]
            rec.sh_vendor_statement_ids=[(6,0,[])]
            rec.sh_customer_due_statement_ids=[(6,0,[])]
            rec.sh_vendor_due_statement_ids=[(6,0,[])]
            
            # ================================================================================
            # PREAPRE DATA FOR CUSTOMER STATEMENT WHICH PARTNER HAS CUSTOMER RANK MORE THAN 0
            # ================================================================================
            
            if rec.customer_rank > 0:
                
                # ------- GET DATA OF INVOICE AND CREDIT NOTE FOR CURRENT PARTNER ----------
                
                self._cr.execute(""" select id from account_move where partner_id=%s and move_type in ('out_invoice','out_refund') and state not in ('draft','cancel') and company_id in %s  """,[rec.id,tuple(company_ids)])
                c_moves_statements=self._cr.dictfetchall()
                c_moves_statements=self.env['account.move'].browse([r['id'] for r in c_moves_statements])
                
                # ------- CREATE CUSTOMER STATEMENT LINE FROM INVOICE ----------
                for move in c_moves_statements.filtered(lambda i:i.move_type=='out_invoice'):
                    statement_vals = {
                        "sh_account": rec.property_account_receivable_id.name,
                        "name": move.name,
                        "currency_id": move.currency_id.id,
                        "sh_customer_invoice_date": move.invoice_date,
                        "sh_customer_due_date": move.invoice_date_due,
                        "sh_customer_amount": move.amount_total,
                        "sh_customer_paid_amount": move.amount_total
                        - move.amount_residual,
                        "sh_customer_balance": move.amount_residual,
                        "partner_id":rec.id,
                    }
                    self.env['sh.customer.statement'].create(statement_vals)
                    
                # ------- CREATE CUSTOMER STATEMENT LINE FROM CREDIT NOTE AND MULTIPLE WITH -1 BECAUSE IT REVERSE OF INVOICE  ----------    
                for move in c_moves_statements.filtered(lambda i:i.move_type=='out_refund'):
                    statement_vals = {
                        "sh_account": rec.property_account_receivable_id.name,
                        "name": move.name,
                        "currency_id": move.currency_id.id,
                        "sh_customer_invoice_date": move.invoice_date,
                        "sh_customer_due_date": move.invoice_date_due,
                        "sh_customer_amount": move.amount_total*-1,
                        "sh_customer_paid_amount": (move.amount_total
                        - move.amount_residual)*-1,
                        "sh_customer_balance": (move.amount_residual)*-1,
                        "partner_id":rec.id,
                    }
                    self.env['sh.customer.statement'].create(statement_vals)
                
                # ================================================================================
                # GET PAYMENT OF CURRENT PARTNER WHICH IS NOT FULLY RECONCILE AND CUSTOMER 
                # RECEVING PAYMENT AND VENDOR SENDED PAYMENT
                # ================================================================================
                
                self._cr.execute(""" select id from account_payment where partner_id=%s and is_reconciled=False and partner_type='customer' and move_id in (select id from account_move where company_id in %s) """,[rec.id,tuple(company_ids)])
                customer_payment=self._cr.dictfetchall()
                customer_payment=self.env['account.payment'].browse([r['id'] for r in customer_payment])
                
                # ------- CREATE CUSTOMER STATEMENT LINE FROM CUSTOMER INBOUND (RECEVING) PAYMENT ----------
                for payment in customer_payment.filtered(lambda i:i.payment_type=='inbound' and i.state=='posted' and i.company_id.id in company_ids):
                    domain = [
                        ('account_id.account_type', 'in',('asset_receivable', 'liability_payable')),
                        ('parent_state', '=', 'posted'),
                        ('payment_id', '=', payment.id),
                    ]
                    unpaid_move=self.env['account.move.line'].search(domain)
                    unpaid_amount=sum(unpaid_move.mapped('amount_residual_currency'))
                    statement_vals = {
                        "sh_account": rec.property_account_receivable_id.name,
                        "name": payment.name,
                        "currency_id": payment.currency_id.id,
                        "sh_customer_invoice_date": payment.date,
                        "sh_customer_amount": 0,
                        "sh_customer_paid_amount": abs(unpaid_amount) ,
                        "sh_customer_balance": unpaid_amount ,
                        "partner_id":rec.id,
                    }
                    self.env['sh.customer.statement'].create(statement_vals) 
                
                # ------- CREATE CUSTOMER STATEMENT LINE FROM VENDOR OUTBOUND (SENDING) PAYMENT ----------
                for payment in customer_payment.filtered(lambda i:i.payment_type=='outbound' and i.state=='posted' and i.company_id.id in company_ids):
                    domain = [
                        ('account_id.account_type', 'in',('asset_receivable', 'liability_payable')),
                        ('parent_state', '=', 'posted'),
                        ('payment_id', '=', payment.id),
                    ]
                    unpaid_move=self.env['account.move.line'].search(domain)
                    unpaid_amount=sum(unpaid_move.mapped('amount_residual_currency'))
                    statement_vals = {
                        "sh_account": rec.property_account_receivable_id.name,
                        "name": payment.name,
                        "currency_id": payment.currency_id.id,
                        "sh_customer_invoice_date": payment.date,
                        "sh_customer_amount": 0,
                        "sh_customer_paid_amount": abs(unpaid_amount) ,
                        "sh_customer_balance": unpaid_amount ,
                        "partner_id":rec.id,
                    }
                    self.env['sh.customer.statement'].create(statement_vals)     
                
                #  ==================================================================
                #  CALCULATE AGING FROM INVOICE AND PAYMENT OF CUSTOMER 
                #  ==================================================================
                current_date=date.today()
                
                # --------- CALCULATE 0 TO 30 DAYS BALANCE AMOUNT -----------------
                
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='out_invoice' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s """,[rec.id,current_date,current_date-timedelta(days=30),tuple(company_ids)])
                invoice_due_amount_0_to_30=self._cr.dictfetchall()
                invoice_due_amount_0_to_30=sum([sub['amount_residual'] for sub in invoice_due_amount_0_to_30 ])
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='out_refund' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s """,[rec.id,current_date,current_date-timedelta(days=30),tuple(company_ids)])
                credit_note_due_amount_0_to_30=self._cr.dictfetchall()
                credit_note_due_amount_0_to_30=sum([sub['amount_residual'] for sub in credit_note_due_amount_0_to_30 ]) 
                payment_0_to_30=customer_payment.filtered(lambda i:i.state=='posted' and i.date<=current_date and i.date>current_date-timedelta(days=30) and i.company_id.id in company_ids)
                payment_due_amount_0_to_30=0
                if payment_0_to_30:
                    self._cr.execute(""" select id,amount_residual_currency from account_move_line where account_id in (select id from account_account where account_type in ('asset_receivable','liability_payable')) and parent_state='posted' and payment_id in %s   """,[tuple(payment_0_to_30.ids),])
                    payment_due_amount_0_to_30=self._cr.dictfetchall()
                    payment_due_amount_0_to_30=sum([sub['amount_residual_currency'] for sub in payment_due_amount_0_to_30 ])
                rec.sh_customer_zero_to_thiry=invoice_due_amount_0_to_30-credit_note_due_amount_0_to_30+payment_due_amount_0_to_30    
                   
                # --------- CALCULATE 30 TO 60 DAYS BALANCE AMOUNT -----------------
                
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='out_invoice' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s  """,[rec.id,current_date-timedelta(days=30),current_date-timedelta(days=60),tuple(company_ids)])
                invoice_due_amount_30_to_60=self._cr.dictfetchall()
                invoice_due_amount_30_to_60=sum([sub['amount_residual'] for sub in invoice_due_amount_30_to_60 ])
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='out_refund' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel')  and company_id in %s """,[rec.id,current_date-timedelta(days=30),current_date-timedelta(days=60),tuple(company_ids)])
                credit_note_due_amount_30_to_60=self._cr.dictfetchall()
                credit_note_due_amount_30_to_60=sum([sub['amount_residual'] for sub in credit_note_due_amount_30_to_60 ]) 
                payment_30_to_60=customer_payment.filtered(lambda i:i.state=='posted' and i.date<=current_date-timedelta(days=30) and i.date>current_date-timedelta(days=60) and i.company_id.id in company_ids)
                payment_due_amount_30_to_60=0
                if payment_30_to_60:
                    self._cr.execute(""" select id,amount_residual_currency from account_move_line where account_id in (select id from account_account where account_type in ('asset_receivable','liability_payable')) and parent_state='posted' and payment_id in %s   """,[tuple(payment_30_to_60.ids),])
                    payment_due_amount_30_to_60=self._cr.dictfetchall()
                    payment_due_amount_30_to_60=sum([sub['amount_residual_currency'] for sub in payment_due_amount_30_to_60 ])
                rec.sh_customer_thirty_to_sixty=invoice_due_amount_30_to_60-credit_note_due_amount_30_to_60+payment_due_amount_30_to_60 
                
                # --------- CALCULATE 60 TO 90 DAYS BALANCE AMOUNT -----------------
                
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='out_invoice' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s  """,[rec.id,current_date-timedelta(days=60),current_date-timedelta(days=90),tuple(company_ids)])
                invoice_due_amount_60_to_90=self._cr.dictfetchall()
                invoice_due_amount_60_to_90=sum([sub['amount_residual'] for sub in invoice_due_amount_60_to_90 ])
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='out_refund' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s  """,[rec.id,current_date-timedelta(days=60),current_date-timedelta(days=90),tuple(company_ids)])
                credit_note_due_amount_60_to_90=self._cr.dictfetchall()
                credit_note_due_amount_60_to_90=sum([sub['amount_residual'] for sub in credit_note_due_amount_60_to_90 ]) 
                payment_60_to_90=customer_payment.filtered(lambda i:i.state=='posted' and i.date<=current_date-timedelta(days=60) and i.date>current_date-timedelta(days=90) and i.company_id.id in company_ids)
                payment_due_amount_60_to_90=0
                if payment_60_to_90:
                    self._cr.execute(""" select id,amount_residual_currency from account_move_line where account_id in (select id from account_account where account_type in ('asset_receivable','liability_payable')) and parent_state='posted' and payment_id in %s   """,[tuple(payment_60_to_90.ids),])
                    payment_due_amount_60_to_90=self._cr.dictfetchall()
                    payment_due_amount_60_to_90=sum([sub['amount_residual_currency'] for sub in payment_due_amount_60_to_90 ])
                rec.sh_customer_sixty_to_ninety=invoice_due_amount_60_to_90-credit_note_due_amount_60_to_90+payment_due_amount_60_to_90 
                
                # --------- CALCULATE 30 TO 60 DAYS BALANCE AMOUNT -----------------
                
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='out_invoice' and invoice_date<=%s  and state not in ('draft','cancel') and company_id in %s  """,[rec.id,current_date-timedelta(days=90),tuple(company_ids)])
                invoice_due_amount_90_plus=self._cr.dictfetchall()
                invoice_due_amount_90_plus=sum([sub['amount_residual'] for sub in invoice_due_amount_90_plus ])
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='out_refund' and invoice_date<=%s  and state not in ('draft','cancel') and company_id in %s  """,[rec.id,current_date-timedelta(days=90),tuple(company_ids)])
                credit_note_due_amount_90_plus=self._cr.dictfetchall()
                credit_note_due_amount_90_plus=sum([sub['amount_residual'] for sub in credit_note_due_amount_90_plus ]) 
                payment_90_plus=customer_payment.filtered(lambda i:i.state=='posted' and i.date<=current_date-timedelta(days=90) and i.company_id.id in company_ids)
                payment_due_amount_90_plus=0
                if payment_90_plus:
                    self._cr.execute(""" select id,amount_residual_currency from account_move_line where account_id in (select id from account_account where account_type in ('asset_receivable','liability_payable')) and parent_state='posted' and payment_id in %s   """,[tuple(payment_90_plus.ids),])
                    payment_due_amount_90_plus=self._cr.dictfetchall()
                    payment_due_amount_90_plus=sum([sub['amount_residual_currency'] for sub in payment_due_amount_90_plus ])
                rec.sh_customer_ninety_plus=invoice_due_amount_90_plus-credit_note_due_amount_90_plus+payment_due_amount_90_plus  
                
                rec.sh_customer_total=rec.sh_customer_zero_to_thiry+rec.sh_customer_thirty_to_sixty+rec.sh_customer_sixty_to_ninety+rec.sh_customer_ninety_plus
                    
                #  ==================================================================
                #  OVERDUE STATEMENT LINE CREATE ACCORDING TO CONFIGURATION IN 
                #  ==================================================================      
                due_invoices=False
                if self.env.company.sh_display_due_statement =='due':
                    due_invoices=c_moves_statements.filtered(lambda x:x.amount_residual>0 and x.invoice_date_due >= current_date  )
                
                elif self.env.company.sh_display_due_statement =='overdue':
                    due_invoices=c_moves_statements.filtered(lambda x:x.amount_residual>0 and x.invoice_date_due < current_date  )
                elif self.env.company.sh_display_due_statement =='both':
                    due_invoices=c_moves_statements.filtered(lambda x:x.amount_residual>0 )
                if due_invoices:
                    for invoice in due_invoices.filtered(lambda i:i.move_type=='out_invoice'):
                        overdue_statement_vals = {
                            "sh_account": rec.property_account_receivable_id.name,
                            "currency_id": invoice.currency_id.id,
                            "name": invoice.name,
                            "sh_today": current_date,
                            "sh_due_customer_invoice_date": invoice.invoice_date,
                            "sh_due_customer_due_date": invoice.invoice_date_due,
                            "partner_id" :rec.id,
                            "sh_due_customer_amount": invoice.amount_total ,
                            "sh_due_customer_paid_amount":invoice.amount_total-invoice.amount_residual ,
                            "sh_due_customer_balance":invoice.amount_residual ,
                        }
                        self.env['sh.customer.due.statement'].create(overdue_statement_vals)
                        
                    # ------- CREATE CUSTOMER STATEMENT LINE FROM CREDIT NOTE AND MULTIPLE WITH -1 BECAUSE IT REVERSE OF INVOICE  ----------    
                    for invoice in due_invoices.filtered(lambda i:i.move_type=='out_refund'):
                        overdue_statement_vals = {
                            "sh_account": rec.property_account_receivable_id.name,
                            "currency_id": invoice.currency_id.id,
                            "name": invoice.name,
                            "sh_today": current_date,
                            "sh_due_customer_invoice_date": invoice.invoice_date,
                            "sh_due_customer_due_date": invoice.invoice_date_due,
                            "partner_id" :rec.id,
                            "sh_due_customer_amount": invoice.amount_total*-1 ,
                            "sh_due_customer_paid_amount":(invoice.amount_total-invoice.amount_residual)*-1 ,
                            "sh_due_customer_balance":invoice.amount_residual*-1 ,
                        }
                        self.env['sh.customer.due.statement'].create(overdue_statement_vals)
                                     
                        
                    
            # =================================================================================
            # =================================================================================        
                    
            if rec.supplier_rank > 0:
                # ------- GET DATA OF BILL AND DEBIT NOTE FOR CURRENT PARTNER ----------
                self._cr.execute(""" select id from account_move where partner_id=%s and move_type in ('in_invoice','in_refund') and state not in ('draft','cancel') and company_id in %s """,[rec.id,tuple(company_ids)])
                v_moves_statements=self._cr.dictfetchall()
                v_moves_statements=self.env['account.move'].browse([r['id'] for r in v_moves_statements])
                # ------- CREATE VENDOR STATEMENT LINE FROM INVOICE ----------
                for move in v_moves_statements.filtered(lambda i:i.move_type=='in_invoice' and i.company_id.id in company_ids):
                    statement_vals = {
                        "sh_account": rec.property_account_receivable_id.name,
                        "name": move.name,
                        "currency_id": move.currency_id.id,
                        "sh_vendor_invoice_date": move.invoice_date,
                        "sh_vendor_due_date": move.invoice_date_due,
                        "sh_vendor_amount": move.amount_total*-1,
                        "sh_vendor_paid_amount": (move.amount_total
                        - move.amount_residual)*-1,
                        "sh_vendor_balance": move.amount_residual*-1,
                        "partner_id":rec.id,
                    }
                    self.env['sh.vendor.statement'].create(statement_vals)
                    
                # ------- CREATE VENDOR STATEMENT LINE FROM CREDIT NOTE AND MULTIPLE WITH -1 BECAUSE IT REVERSE OF INVOICE  ----------    
                for move in v_moves_statements.filtered(lambda i:i.move_type=='in_refund' and i.company_id.id in company_ids):
                    statement_vals = {
                        "sh_account": rec.property_account_receivable_id.name,
                        "name": move.name,
                        "currency_id": move.currency_id.id,
                        "sh_vendor_invoice_date": move.invoice_date,
                        "sh_vendor_due_date": move.invoice_date_due,
                        "sh_vendor_amount": move.amount_total,
                        "sh_vendor_paid_amount": (move.amount_total
                        - move.amount_residual),
                        "sh_vendor_balance": (move.amount_residual),
                        "partner_id":rec.id,
                    }
                    self.env['sh.vendor.statement'].create(statement_vals)
                
                # ================================================================================
                # GET PAYMENT OF CURRENT PARTNER WHICH IS NOT FULLY RECONCILE AND VENDOR 
                # RECEVING PAYMENT AND CUSTOMER SENDED PAYMENT
                # ================================================================================
                
                self._cr.execute(""" select id from account_payment where partner_id=%s and is_reconciled=False and partner_type='supplier'  and move_id in (select id from account_move where company_id in %s) """,[rec.id,tuple(company_ids)])
                vendor_payment=self._cr.dictfetchall()
                vendor_payment=self.env['account.payment'].browse([r['id'] for r in vendor_payment])
                
                # ------- CREATE VENDOR STATEMENT LINE FROM VENDOR INBOUND (RECEVING) PAYMENT ----------
                for payment in vendor_payment.filtered(lambda i:i.payment_type=='inbound' and i.state=='posted' and i.company_id.id in company_ids):
                    domain = [
                        ('account_id.account_type', 'in',('asset_receivable', 'liability_payable')),
                        ('parent_state', '=', 'posted'),
                        ('payment_id', '=', payment.id),
                    ]
                    unpaid_move=self.env['account.move.line'].search(domain)
                    unpaid_amount=sum(unpaid_move.mapped('amount_residual_currency'))
                    statement_vals = {
                        "sh_account": rec.property_account_receivable_id.name,
                        "name": payment.name,
                        "currency_id": payment.currency_id.id,
                        "sh_vendor_invoice_date": payment.date,
                        "sh_vendor_amount": 0,
                        "sh_vendor_paid_amount": abs(unpaid_amount) ,
                        "sh_vendor_balance": unpaid_amount ,
                        "partner_id":rec.id,
                    }
                    self.env['sh.vendor.statement'].create(statement_vals) 
                
                # ------- CREATE VENDOR STATEMENT LINE FROM CUSTOMER OUTBOUND (SENDING) PAYMENT ----------
                for payment in vendor_payment.filtered(lambda i:i.payment_type=='outbound' and i.state=='posted' and i.company_id.id in company_ids):
                    domain = [
                        ('account_id.account_type', 'in',('asset_receivable', 'liability_payable')),
                        ('parent_state', '=', 'posted'),
                        ('payment_id', '=', payment.id),
                    ]
                    unpaid_move=self.env['account.move.line'].search(domain)
                    unpaid_amount=sum(unpaid_move.mapped('amount_residual_currency'))
                    statement_vals = {
                        "sh_account": rec.property_account_receivable_id.name,
                        "name": payment.name,
                        "currency_id": payment.currency_id.id,
                        "sh_vendor_invoice_date": payment.date,
                        "sh_vendor_amount": 0,
                        "sh_vendor_paid_amount": abs(unpaid_amount) ,
                        "sh_vendor_balance": unpaid_amount ,
                        "partner_id":rec.id,
                    }
                    self.env['sh.vendor.statement'].create(statement_vals) 
                
                #  ==================================================================
                #  CALCULATE AGING FROM INVOICE AND PAYMENT OF VENDOR 
                #  ==================================================================
                
                current_date=date.today()
                
                # --------- CALCULATE 0 TO 30 DAYS BALANCE AMOUNT -----------------
                
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='in_invoice' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s """,[rec.id,current_date,current_date-timedelta(days=30),tuple(company_ids)])
                bill_due_amount_0_to_30=self._cr.dictfetchall()
                bill_due_amount_0_to_30=sum([sub['amount_residual'] for sub in bill_due_amount_0_to_30 ])
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='in_refund' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s """,[rec.id,current_date,current_date-timedelta(days=30),tuple(company_ids)])
                debit_note_due_amount_0_to_30=self._cr.dictfetchall()
                debit_note_due_amount_0_to_30=sum([sub['amount_residual'] for sub in debit_note_due_amount_0_to_30 ]) 
                payment_0_to_30=vendor_payment.filtered(lambda i:i.state=='posted' and i.date<=current_date and i.date>current_date-timedelta(days=30) and i.company_id.id in company_ids)
                payment_due_amount_0_to_30=0
                if payment_0_to_30:
                    self._cr.execute(""" select id,amount_residual_currency from account_move_line where account_id in (select id from account_account where account_type in ('asset_receivable','liability_payable')) and parent_state='posted' and payment_id in %s   """,[tuple(payment_0_to_30.ids),])
                    payment_due_amount_0_to_30=self._cr.dictfetchall()
                    payment_due_amount_0_to_30=sum([sub['amount_residual_currency'] for sub in payment_due_amount_0_to_30 ])
                
                rec.sh_vendor_zero_to_thiry=debit_note_due_amount_0_to_30-bill_due_amount_0_to_30+payment_due_amount_0_to_30    
                   
                # --------- CALCULATE 30 TO 60 DAYS BALANCE AMOUNT -----------------
                
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='in_invoice' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s """,[rec.id,current_date-timedelta(days=30),current_date-timedelta(days=60),tuple(company_ids)])
                bill_due_amount_30_to_60=self._cr.dictfetchall()
                bill_due_amount_30_to_60=sum([sub['amount_residual'] for sub in bill_due_amount_30_to_60 ])
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='in_refund' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s """,[rec.id,current_date-timedelta(days=30),current_date-timedelta(days=60),tuple(company_ids)])
                debit_note_due_amount_30_to_60=self._cr.dictfetchall()
                debit_note_due_amount_30_to_60=sum([sub['amount_residual'] for sub in debit_note_due_amount_30_to_60 ]) 
                payment_30_to_60=vendor_payment.filtered(lambda i:i.state=='posted' and i.date<=current_date-timedelta(days=30) and i.date>current_date-timedelta(days=60) and i.company_id.id in company_ids)
                payment_due_amount_30_to_60=0
                if payment_30_to_60:
                    self._cr.execute(""" select id,amount_residual_currency from account_move_line where account_id in (select id from account_account where account_type in ('asset_receivable','liability_payable')) and parent_state='posted' and payment_id in %s   """,[tuple(payment_30_to_60.ids),])
                    payment_due_amount_30_to_60=self._cr.dictfetchall()
                    payment_due_amount_30_to_60=sum([sub['amount_residual_currency'] for sub in payment_due_amount_30_to_60 ])
                
                rec.sh_vendor_thirty_to_sixty=debit_note_due_amount_30_to_60-bill_due_amount_30_to_60+payment_due_amount_30_to_60 
                
                # --------- CALCULATE 60 TO 90 DAYS BALANCE AMOUNT -----------------
                
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='in_invoice' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s """,[rec.id,current_date-timedelta(days=60),current_date-timedelta(days=90),tuple(company_ids)])
                bill_due_amount_60_to_90=self._cr.dictfetchall()
                bill_due_amount_60_to_90=sum([sub['amount_residual'] for sub in bill_due_amount_60_to_90 ])
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='in_refund' and invoice_date<=%s and  invoice_date>%s  and state not in ('draft','cancel') and company_id in %s """,[rec.id,current_date-timedelta(days=60),current_date-timedelta(days=90),tuple(company_ids)])
                debit_note_due_amount_60_to_90=self._cr.dictfetchall()
                debit_note_due_amount_60_to_90=sum([sub['amount_residual'] for sub in debit_note_due_amount_60_to_90 ]) 
                payment_60_to_90=vendor_payment.filtered(lambda i:i.state=='posted' and i.date<=current_date-timedelta(days=60) and i.date>current_date-timedelta(days=90) and i.company_id.id in company_ids)
                payment_due_amount_60_to_90=0
                if payment_60_to_90:
                    self._cr.execute(""" select id,amount_residual_currency from account_move_line where account_id in (select id from account_account where account_type in ('asset_receivable','liability_payable')) and parent_state='posted' and payment_id in %s   """,[tuple(payment_60_to_90.ids),])
                    payment_due_amount_60_to_90=self._cr.dictfetchall()
                    payment_due_amount_60_to_90=sum([sub['amount_residual_currency'] for sub in payment_due_amount_60_to_90 ])
                rec.sh_vendor_sixty_to_ninety=debit_note_due_amount_60_to_90-bill_due_amount_60_to_90+payment_due_amount_60_to_90 
                
                # --------- CALCULATE 30 TO 60 DAYS BALANCE AMOUNT -----------------
                
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='in_invoice' and invoice_date<=%s  and state not in ('draft','cancel') and company_id in %s  """,[rec.id,current_date-timedelta(days=90),tuple(company_ids)])
                bill_due_amount_90_plus=self._cr.dictfetchall()
                bill_due_amount_90_plus=sum([sub['amount_residual'] for sub in bill_due_amount_90_plus ])
                self._cr.execute(""" select id,amount_residual from account_move where partner_id=%s and move_type ='in_refund' and invoice_date<=%s  and state not in ('draft','cancel') and company_id in %s  """,[rec.id,current_date-timedelta(days=90),tuple(company_ids)])
                debit_note_due_amount_90_plus=self._cr.dictfetchall()
                debit_note_due_amount_90_plus=sum([sub['amount_residual'] for sub in debit_note_due_amount_90_plus ]) 
                payment_90_plus=vendor_payment.filtered(lambda i:i.state=='posted' and i.date<=current_date-timedelta(days=90) and i.company_id.id in company_ids)
                payment_due_amount_90_plus=0
                if payment_90_plus:
                    self._cr.execute(""" select id,amount_residual_currency from account_move_line where account_id in (select id from account_account where account_type in ('asset_receivable','liability_payable')) and parent_state='posted' and payment_id in %s   """,[tuple(payment_90_plus.ids),])
                    payment_due_amount_90_plus=self._cr.dictfetchall()
                    payment_due_amount_90_plus=sum([sub['amount_residual_currency'] for sub in payment_due_amount_90_plus ])
                rec.sh_vendor_ninety_plus=debit_note_due_amount_90_plus-bill_due_amount_90_plus+payment_due_amount_90_plus  
            
                rec.sh_vendor_total=rec.sh_vendor_zero_to_thiry+rec.sh_vendor_thirty_to_sixty+rec.sh_vendor_sixty_to_ninety+rec.sh_vendor_ninety_plus

                #  ==================================================================
                #  OVERDUE STATEMENT LINE CREATE ACCORDING TO CONFIGURATION IN 
                #  ==================================================================    
                due_bill=False
                if self.env.company.sh_display_due_statement =='due':
                    due_bill=v_moves_statements.filtered(lambda x:x.amount_residual>0 and x.invoice_date_due >= current_date  )
                elif self.env.company.sh_display_due_statement =='overdue':
                    due_bill=v_moves_statements.filtered(lambda x:x.amount_residual>0 and x.invoice_date_due < current_date  )
                elif self.env.company.sh_display_due_statement =='both':
                    due_bill=v_moves_statements.filtered(lambda x:x.amount_residual>0 )
                if due_bill:
                    for bill in due_bill.filtered(lambda i:i.move_type=='in_invoice'):
                        overdue_statement_vals = {
                            "sh_account": rec.property_account_receivable_id.name,
                            "currency_id": bill.currency_id.id,
                            "name": bill.name,
                            "sh_today": current_date,
                            "sh_due_vendor_invoice_date": bill.invoice_date,
                            "sh_due_vendor_due_date": bill.invoice_date_due,
                            "partner_id" :rec.id,
                            "sh_due_vendor_amount": bill.amount_total*-1 ,
                            "sh_due_vendor_paid_amount":(bill.amount_total-bill.amount_residual )*-1,
                            "sh_due_vendor_balance":bill.amount_residual*-1 ,
                        }
                        self.env['sh.vendor.due.statement'].create(overdue_statement_vals)
                        
                    # ------- CREATE VENDOR STATEMENT LINE FROM CREDIT NOTE AND MULTIPLE WITH -1 BECAUSE IT REVERSE OF INVOICE  ----------    
                    for bill in due_bill.filtered(lambda i:i.move_type=='in_refund'):
                        overdue_statement_vals = {
                            "sh_account": rec.property_account_receivable_id.name,
                            "currency_id": bill.currency_id.id,
                            "name": bill.name,
                            "sh_today": current_date,
                            "sh_due_vendor_invoice_date": bill.invoice_date,
                            "sh_due_vendor_due_date": bill.invoice_date_due,
                            "partner_id" :rec.id,
                            "sh_due_vendor_amount": bill.amount_total ,
                            "sh_due_vendor_paid_amount":bill.amount_total-bill.amount_residual ,
                            "sh_due_vendor_balance":bill.amount_residual ,
                        }
                        self.env['sh.vendor.due.statement'].create(overdue_statement_vals)
                    
                     

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        if self.filtered(lambda c: c.end_date and c.start_date and c.start_date > c.end_date):
            raise ValidationError(_("start date must be less than end date."))

    def _compute_statement_portal_url_wp(self):
        for rec in self:
            rec.portal_statement_url_wp = False
            if rec.company_id.sh_statement_url_in_message:
                base_url = (
                    self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                )
                ticket_url = ""
                if rec.customer_rank > 0:
                    ticket_url = base_url + "/my/customer_statements"
                elif rec.supplier_rank > 0:
                    ticket_url = base_url + "/my/vendor_statements"
                rec.portal_statement_url_wp = ticket_url

    def _get_token(self):
        """Get the current record access token"""
        if self.report_token:
            return self.report_token
        else:
            report_token = str(uuid.uuid4())
            self.write({"report_token": report_token})
            return report_token

    def get_download_report_url(self):
        url = ""
        if self.id:
            self.ensure_one()
            url = "/download/cfs/" + "%s?access_token=%s" % (self.id, self._get_token())
        return url

    def get_download_vfs_report_url(self):
        url = ""
        if self.id:
            self.ensure_one()
            url = "/download/vfs/" + "%s?access_token=%s" % (self.id, self._get_token())
        return url

    def get_cust_statement_download_report_url(self):
        url = ""
        if self.id:
            self.ensure_one()
            url = "/download/cs/" + "%s?access_token=%s" % (self.id, self._get_token())
        return url

    def get_vend_statement_download_report_url(self):
        url = ""
        if self.id:
            self.ensure_one()
            url = "/download/vs/" + "%s?access_token=%s" % (self.id, self._get_token())
        return url

    def get_cust_due_statement_download_report_url(self):
        url = ""
        if self.id:
            self.ensure_one()
            url = "/download/cds/" + "%s?access_token=%s" % (self.id, self._get_token())
        return url

    def get_vend_due_statement_download_report_url(self):
        url = ""
        if self.id:
            self.ensure_one()
            url = "/download/vds/" + "%s?access_token=%s" % (self.id, self._get_token())
        return url

    def _compute_cfs_report_url(self):
        for rec in self:
            rec.sh_cfs_statement_report_url = False
            if rec.company_id.sh_statement_pdf_in_message:
                base_url = (
                    self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                )
                if rec.customer_rank > 0:
                    rec.sh_cfs_statement_report_url = (
                        base_url + rec.get_download_report_url()
                    )

    def _compute_vfs_report_url(self):
        for rec in self:
            rec.sh_vfs_statement_report_url = False
            if rec.company_id.sh_statement_pdf_in_message:
                base_url = (
                    self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                )
                if rec.supplier_rank > 0:
                    rec.sh_vfs_statement_report_url = (
                        base_url + rec.get_download_vfs_report_url()
                    )

    def _compute_cust_report_url(self):
        for rec in self:
            rec.sh_cust_statement_report_url = False
            if rec.company_id.sh_statement_pdf_in_message:
                base_url = (
                    self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                )
                if rec.customer_rank > 0:
                    rec.sh_cust_statement_report_url = (
                        base_url + rec.get_cust_statement_download_report_url()
                    )

    def _compute_vend_report_url(self):
        for rec in self:
            rec.sh_vend_statement_report_url = False
            if rec.company_id.sh_statement_pdf_in_message:
                base_url = (
                    self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                )
                if rec.supplier_rank > 0:
                    rec.sh_vend_statement_report_url = (
                        base_url + rec.get_vend_statement_download_report_url()
                    )

    def _compute_cust_due_report_url(self):
        for rec in self:
            rec.sh_cust_due_statement_report_url = False
            if rec.company_id.sh_statement_pdf_in_message:
                base_url = (
                    self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                )
                if rec.customer_rank > 0:
                    rec.sh_cust_due_statement_report_url = (
                        base_url + rec.get_cust_due_statement_download_report_url()
                    )

    def _compute_vend_due_report_url(self):
        for rec in self:
            rec.sh_vend_due_statement_report_url = False
            if rec.company_id.sh_statement_pdf_in_message:
                base_url = (
                    self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                )
                if rec.supplier_rank > 0:
                    rec.sh_vend_due_statement_report_url = (
                        base_url + rec.get_vend_due_statement_download_report_url()
                    )

    def _get_cfs_report_base_filename(self):
        self.ensure_one()
        return "%s %s" % ("Customer Statement Filter By Date", self.name)

    def _get_vfs_report_base_filename(self):
        self.ensure_one()
        return "%s %s" % ("Vendor Statement Filter By Date", self.name)

    def _get_cs_report_base_filename(self):
        self.ensure_one()
        return "%s %s" % ("Customer Statement", self.name)

    def _get_vs_report_base_filename(self):
        self.ensure_one()
        return "%s %s" % ("Vendor Statement", self.name)

    def _get_cds_report_base_filename(self):
        self.ensure_one()
        return "%s %s" % ("Customer Due/Overdue Statement", self.name)

    def _get_vds_report_base_filename(self):
        self.ensure_one()
        return "%s %s" % ("Vendor Due/Overdue Statement", self.name)

    def action_send_filter_customer_whatsapp(self):
        self.ensure_one()
        if not self.mobile:
            raise UserError(_("Partner Mobile Number Not Exist !"))
        template = self.env.ref(
            "sh_account_statement.sh_send_customer_filter_whatsapp_email_template"
        )
        ctx = {
            "default_model": "res.partner",
            "default_res_ids": self.ids,
            "default_use_template": bool(template.id),
            "default_template_id": template.id,
            "default_composition_mode": "comment",
            "force_email": True,
            "default_is_customer_statement": True,
        }
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": ctx,
        }

    def action_send_filter_vendor_whatsapp(self):
        self.ensure_one()
        if not self.mobile:
            raise UserError(_("Partner Mobile Number Not Exist !"))
        template = self.env.ref(
            "sh_account_statement.sh_send_vendor_filter_whatsapp_email_template"
        )
        ctx = {
            "default_model": "res.partner",
            "default_res_ids": self.ids,
            "default_use_template": bool(template.id),
            "default_template_id": template.id,
            "default_composition_mode": "comment",
            "force_email": True,
            "default_is_vendor_statement": True,
        }
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": ctx,
        }

    def action_send_customer_whatsapp(self):
        self.ensure_one()
        if not self.mobile:
            raise UserError(_("Partner Mobile Number Not Exist !"))
        template = self.env.ref(
            "sh_account_statement.sh_send_customer_whatsapp_email_template"
        )
        ctx = {
            "default_model": "res.partner",
            "default_res_ids": self.ids,
            "default_use_template": bool(template.id),
            "default_template_id": template.id,
            "default_composition_mode": "comment",
            "force_email": True,
            "default_is_customer_statement": True,
        }
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": ctx,
        }

    def action_send_vendor_whatsapp(self):
        self.ensure_one()
        if not self.mobile:
            raise UserError(_("Partner Mobile Number Not Exist !"))
        template = self.env.ref(
            "sh_account_statement.sh_send_vendor_whatsapp_email_template"
        )
        ctx = {
            "default_model": "res.partner",
            "default_res_ids": self.ids,
            "default_use_template": bool(template.id),
            "default_template_id": template.id,
            "default_composition_mode": "comment",
            "force_email": True,
            "default_is_vendor_statement": True,
        }
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": ctx,
        }

    def action_send_due_customer_whatsapp(self):
        self.ensure_one()
        if not self.mobile:
            raise UserError(_("Partner Mobile Number Not Exist !"))
        template = self.env.ref(
            "sh_account_statement.sh_send_customer_due_whatsapp_email_template"
        )
        ctx = {
            "default_model": "res.partner",
            "default_res_ids": self.ids,
            "default_use_template": bool(template.id),
            "default_template_id": template.id,
            "default_composition_mode": "comment",
            "force_email": True,
            "default_is_customer_statement": True,
        }
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": ctx,
        }

    def action_send_due_vendor_whatsapp(self):
        self.ensure_one()
        if not self.mobile:
            raise UserError(_("Partner Mobile Number Not Exist !"))
        template = self.env.ref(
            "sh_account_statement.sh_send_vend_due_whatsapp_email_template"
        )
        ctx = {
            "default_model": "res.partner",
            "default_res_ids": self.ids,
            "default_use_template": bool(template.id),
            "default_template_id": template.id,
            "default_composition_mode": "comment",
            "force_email": True,
            "default_is_vendor_statement": True,
        }
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": ctx,
        }

    def update_statement_config_manually_(self):
        view = self.env.ref("sh_account_statement.sh_update_statement_config_wizard")
        return {
            "name": "Mass Update Config",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [(view.id, "form")],
            "res_model": "sh.partners.config.mass.update",
            "view_id": view.id,
            "target": "new",
            "context": {"default_sh_selected_partner_ids": self.ids},
        }

    def send_statement(self):
        for rec in self:
            if rec.customer_rank > 0 and rec.sh_customer_statement_ids:
                template = self.env.ref(
                    "sh_account_statement.sh_customer_statement_mail_template"
                )
                if template:
                    mail = template.sudo().send_mail(rec.id, force_send=True)
                    mail_id = self.env["mail.mail"].sudo().browse(mail)
                    if mail_id:
                        self.env["sh.partner.mail.history"].sudo().create(
                            {
                                "name": "Customer Account Statement",
                                "sh_statement_type": "customer_statement",
                                "sh_current_date": fields.Datetime.now(),
                                "sh_partner_id": rec.id,
                                "sh_mail_id": mail_id.id,
                                "sh_mail_status": mail_id.state,
                            }
                        )
            if rec.supplier_rank > 0 and rec.sh_vendor_statement_ids:
                template = self.env.ref(
                    "sh_account_statement.sh_vendor_statement_mail_template"
                )
                if template:
                    mail = template.sudo().send_mail(rec.id, force_send=True)
                    mail_id = self.env["mail.mail"].sudo().browse(mail)
                    if mail_id:
                        self.env["sh.partner.mail.history"].sudo().create(
                            {
                                "name": "Vendor Account Statement",
                                "sh_statement_type": "vendor_statement",
                                "sh_current_date": fields.Datetime.now(),
                                "sh_partner_id": rec.id,
                                "sh_mail_id": mail_id.id,
                                "sh_mail_status": mail_id.state,
                            }
                        )

    def send_overdue_statement(self):
        for rec in self:
            if rec.customer_rank > 0 and rec.sh_customer_due_statement_ids:
                template = self.env.ref(
                    "sh_account_statement.sh_customer_due_statement_mail_template"
                )
                if template:
                    mail = template.sudo().send_mail(rec.id, force_send=True)
                    mail_id = self.env["mail.mail"].sudo().browse(mail)
                    if mail_id:
                        self.env["sh.partner.mail.history"].sudo().create(
                            {
                                "name": "Customer Account Overdue Statement",
                                "sh_statement_type": "customer_overdue_statement",
                                "sh_current_date": fields.Datetime.now(),
                                "sh_partner_id": rec.id,
                                "sh_mail_id": mail_id.id,
                                "sh_mail_status": mail_id.state,
                            }
                        )
            if rec.supplier_rank > 0 and rec.sh_vendor_due_statement_ids:
                template = self.env.ref(
                    "sh_account_statement.sh_vendor_due_statement_mail_template"
                )
                if template:
                    mail = template.sudo().send_mail(rec.id, force_send=True)
                    mail_id = self.env["mail.mail"].sudo().browse(mail)
                    if mail_id:
                        self.env["sh.partner.mail.history"].sudo().create(
                            {
                                "name": "Vendor Account Overdue Statement",
                                "sh_statement_type": "vendor_overdue_statement",
                                "sh_current_date": fields.Datetime.now(),
                                "sh_partner_id": rec.id,
                                "sh_mail_id": mail_id.id,
                                "sh_mail_status": mail_id.state,
                            }
                        )

    def action_print_customer_statement(self):
        return self.env.ref(
            "sh_account_statement.action_report_sh_customer_statement"
        ).report_action(self)

    def action_send_customer_statement(self):
        self.ensure_one()
        template = self.env.ref(
            "sh_account_statement.sh_customer_statement_mail_template"
        )
        if template:
            mail = template.sudo().send_mail(self.id, force_send=True)
            mail_id = self.env["mail.mail"].sudo().browse(mail)
            if mail_id:
                self.env["sh.partner.mail.history"].sudo().create(
                    {
                        "name": "Customer Account Statement",
                        "sh_statement_type": "customer_statement",
                        "sh_current_date": fields.Datetime.now(),
                        "sh_partner_id": self.id,
                        "sh_mail_id": mail_id.id,
                        "sh_mail_status": mail_id.state,
                    }
                )

    def action_print_customer_statement_xls(self):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            "font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        normal = xlwt.easyxf("font:bold True;align: horiz center;align: vert center")
        cyan_text = xlwt.easyxf(
            "font:bold True,color aqua;align: horiz center;align: vert center"
        )
        green_text = xlwt.easyxf(
            "font:bold True,color green;align: horiz center;align: vert center"
        )
        red_text = xlwt.easyxf(
            "font:bold True,color red;align: horiz center;align: vert center"
        )
        bold_center = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        totals = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        worksheet = workbook.add_sheet("Customer Statement", cell_overwrite_ok=True)

        worksheet.row(5).height = 400
        worksheet.row(12).height = 400
        worksheet.row(13).height = 400
        worksheet.row(10).height = 350
        worksheet.row(11).height = 350
        worksheet.col(2).width = 4800
        worksheet.col(3).width = 4800
        worksheet.col(4).width = 5500
        worksheet.col(5).width = 5500
        worksheet.col(6).width = 5500
        worksheet.col(0).width = 5500
        worksheet.col(1).width = 6000
        worksheet.write_merge(2, 3, 0, 6, self.name, heading_format)
        worksheet.write(5, 0, "Number", bold_center)
        worksheet.write(5, 1, "Account", bold_center)
        worksheet.write(5, 2, "Date", bold_center)
        worksheet.write(5, 3, "Due Date", bold_center)
        worksheet.write(5, 4, "Total Amount", bold_center)
        worksheet.write(5, 5, "Paid Amount", bold_center)
        worksheet.write(5, 6, "Balance", bold_center)

        total_amount = 0
        total_paid_amount = 0
        total_balance = 0
        k = 6

        if self.sh_customer_statement_ids:
            for i in self.sh_customer_statement_ids:
                for j in i:
                    worksheet.row(k).height = 350
                    if j.sh_customer_amount == j.sh_customer_balance:
                        if j.name == "Opening Balance":
                            worksheet.write(k, 0, j.name, green_text)
                            worksheet.write(k, 1, j.sh_account, green_text)
                            worksheet.write(
                                k, 2, str(j.sh_customer_invoice_date), green_text
                            )
                            if j.sh_customer_due_date:
                                worksheet.write(
                                    k, 3, str(j.sh_customer_due_date), green_text
                                )
                            else:
                                worksheet.write(k, 3, "", green_text)
                            worksheet.write(
                                k,
                                4,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_customer_amount)),
                                green_text,
                            )
                            worksheet.write(
                                k,
                                5,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_customer_paid_amount)),
                                green_text,
                            )
                            worksheet.write(
                                k,
                                6,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_customer_balance)),
                                green_text,
                            )
                        else:
                            worksheet.write(k, 0, j.name, cyan_text)
                            worksheet.write(k, 1, j.sh_account, cyan_text)
                            worksheet.write(
                                k, 2, str(j.sh_customer_invoice_date), cyan_text
                            )
                            if j.sh_customer_due_date:
                                worksheet.write(
                                    k, 3, str(j.sh_customer_due_date), cyan_text
                                )
                            else:
                                worksheet.write(k, 3, "", cyan_text)
                            worksheet.write(
                                k,
                                4,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_customer_amount)),
                                cyan_text,
                            )
                            worksheet.write(
                                k,
                                5,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_customer_paid_amount)),
                                cyan_text,
                            )
                            worksheet.write(
                                k,
                                6,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_customer_balance)),
                                cyan_text,
                            )
                    elif j.sh_customer_balance == 0:
                        worksheet.write(k, 0, j.name, green_text)
                        worksheet.write(k, 1, j.sh_account, green_text)
                        worksheet.write(
                            k, 2, str(j.sh_customer_invoice_date), green_text
                        )
                        if j.sh_customer_due_date:
                            worksheet.write(
                                k, 3, str(j.sh_customer_due_date), green_text
                            )
                        else:
                            worksheet.write(k, 3, "", green_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_customer_amount)),
                            green_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_customer_paid_amount)),
                            green_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_customer_balance)),
                            green_text,
                        )
                    else:
                        worksheet.write(k, 0, j.name, red_text)
                        worksheet.write(k, 1, j.sh_account, red_text)
                        worksheet.write(k, 2, str(j.sh_customer_invoice_date), red_text)
                        if j.sh_customer_due_date:
                            worksheet.write(k, 3, str(j.sh_customer_due_date), red_text)
                        else:
                            worksheet.write(k, 3, "", red_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_customer_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_customer_paid_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_customer_balance)),
                            red_text,
                        )
                    k = k + 1
                total_amount = total_amount + float(
                    "{:.2f}".format(j.sh_customer_amount)
                )
                total_paid_amount = total_paid_amount + float(
                    "{:.2f}".format(j.sh_customer_paid_amount)
                )
                total_balance = total_balance + j.sh_customer_balance

        if self.sh_customer_statement_ids:
            worksheet.write(k, 4, str("{:.2f}".format(total_amount)), totals)
            worksheet.row(k).height = 350
            worksheet.write(k, 5, str("{:.2f}".format(total_paid_amount)), totals)
            worksheet.write(k, 6, str("{:.2f}".format(total_balance)), totals)
        worksheet.write(k + 3, 0, "Gap Between Days", bold_center)
        worksheet.write(k + 3, 1, "0-30(Days)", bold_center)
        worksheet.write(k + 3, 2, "30-60(Days)", bold_center)
        worksheet.write(k + 3, 3, "60-90(Days)", bold_center)
        worksheet.write(k + 3, 4, "90+(Days)", bold_center)
        worksheet.write(k + 3, 5, "Total", bold_center)
        worksheet.write(k + 4, 0, "Balance Amount", bold_center)
        if self.sh_customer_statement_ids:
            worksheet.write(
                k + 4, 1, str("{:.2f}".format(self.sh_customer_zero_to_thiry)), normal
            )
            worksheet.write(
                k + 4, 2, str("{:.2f}".format(self.sh_customer_thirty_to_sixty)), normal
            )
            worksheet.write(
                k + 4, 3, str("{:.2f}".format(self.sh_customer_sixty_to_ninety)), normal
            )
            worksheet.write(
                k + 4, 4, str("{:.2f}".format(self.sh_customer_ninety_plus)), normal
            )
            worksheet.write(
                k + 4, 5, str("{:.2f}".format(self.sh_customer_total)), normal
            )

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env["ir.attachment"]
        attachment_vals = {
            "name": "Customer Statement.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search(
            [
                ("name", "=", "Customer Statement"),
                ("type", "=", "binary"),
                ("res_model", "=", "ir.ui.view"),
            ],
            limit=1,
        )
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)
        # TODO: make user error here
        if not attachment:
            raise UserError("There is no attachments...")

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "current",
        }

    def action_print_customer_due_statement(self):
        return self.env.ref(
            "sh_account_statement.action_report_sh_customer_due_statement"
        ).report_action(self)

    def action_send_customer_due_statement(self):
        self.ensure_one()
        template = self.env.ref(
            "sh_account_statement.sh_customer_due_statement_mail_template"
        )
        if template:
            mail = template.sudo().send_mail(self.id, force_send=True)
            mail_id = self.env["mail.mail"].sudo().browse(mail)
            if mail_id:
                self.env["sh.partner.mail.history"].sudo().create(
                    {
                        "name": "Customer Account Overdue Statement",
                        "sh_statement_type": "customer_overdue_statement",
                        "sh_current_date": fields.Datetime.now(),
                        "sh_partner_id": self.id,
                        "sh_mail_id": mail_id.id,
                        "sh_mail_status": mail_id.state,
                    }
                )

    def action_print_customer_due_statement_xls(self):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            "font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        red_text = xlwt.easyxf(
            "font:bold True,color red;align: horiz center;align: vert center"
        )
        center_text = xlwt.easyxf("align: horiz center;align: vert center")
        bold_center = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        date = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;borders: left thin, right thin, bottom thin;align: vert center;align: horiz left"
        )
        worksheet = workbook.add_sheet(
            "Customer Overdue Statement", cell_overwrite_ok=True
        )

        now = datetime.now()
        today_date = now.strftime("%d/%m/%Y %H:%M:%S")

        worksheet.write(1, 0, str(str("Date") + str(": ") + str(today_date)), date)
        worksheet.row(1).height = 350
        worksheet.row(6).height = 350
        worksheet.col(0).width = 8000
        worksheet.col(1).width = 6000
        worksheet.col(2).width = 4800
        worksheet.col(3).width = 4800
        worksheet.col(4).width = 5500
        worksheet.col(5).width = 5500
        worksheet.col(6).width = 5500
        worksheet.row(11).height = 350

        worksheet.write_merge(3, 4, 0, 6, self.name, heading_format)
        worksheet.write(6, 0, "Number", bold_center)
        worksheet.write(6, 1, "Account", bold_center)
        worksheet.write(6, 2, "Date", bold_center)
        worksheet.write(6, 3, "Due Date", bold_center)
        worksheet.write(6, 4, "Total Amount", bold_center)
        worksheet.write(6, 5, "Paid Amount", bold_center)
        worksheet.write(6, 6, "Balance", bold_center)

        total_amount = 0
        total_paid_amount = 0
        total_balance = 0
        k = 7

        if self.sh_customer_due_statement_ids:
            for i in self.sh_customer_due_statement_ids:
                worksheet.row(k).height = 350
                for j in i:
                    if (
                        j.sh_due_customer_due_date
                        and j.sh_today
                        and j.sh_due_customer_due_date < j.sh_today
                    ):
                        worksheet.write(k, 0, j.name, red_text)
                        worksheet.write(k, 1, j.sh_account, red_text)
                        worksheet.write(
                            k, 2, str(j.sh_due_customer_invoice_date), red_text
                        )
                        if j.sh_due_customer_due_date:
                            worksheet.write(
                                k, 3, str(j.sh_due_customer_due_date), red_text
                            )
                        else:
                            worksheet.write(k, 3, "", red_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_customer_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_customer_paid_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_customer_balance)),
                            red_text,
                        )
                    else:
                        worksheet.write(k, 0, j.name, center_text)
                        worksheet.write(k, 1, j.sh_account, center_text)
                        worksheet.write(
                            k, 2, str(j.sh_due_customer_invoice_date), center_text
                        )
                        if j.sh_due_customer_due_date:
                            worksheet.write(
                                k, 3, str(j.sh_due_customer_due_date), center_text
                            )
                        else:
                            worksheet.write(k, 3, "", center_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_customer_amount)),
                            center_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_customer_paid_amount)),
                            center_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_customer_balance)),
                            center_text,
                        )
                    k = k + 1
                total_amount = total_amount + j.sh_due_customer_amount
                total_paid_amount = total_paid_amount + j.sh_due_customer_paid_amount
                total_balance = total_balance + j.sh_due_customer_balance
        if self.sh_customer_due_statement_ids:
            worksheet.write(k, 4, str("{:.2f}".format(total_amount)), bold_center)
            worksheet.row(k).height = 350
            worksheet.write(k, 5, str("{:.2f}".format(total_paid_amount)), bold_center)
            worksheet.write(k, 6, str("{:.2f}".format(total_balance)), bold_center)

        fp = io.BytesIO()
        workbook.save(fp)

        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env["ir.attachment"]
        attachment_vals = {
            "name": "Customer Overdue Statement.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search(
            [
                ("name", "=", "Customer Overdue Statement"),
                ("type", "=", "binary"),
                ("res_model", "=", "ir.ui.view"),
            ],
            limit=1,
        )
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)
        # TODO: make user error here
        if not attachment:
            raise UserError("There is no attachments...")

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "current",
        }

    def action_print_vendor_statement(self):
        return self.env.ref(
            "sh_account_statement.action_report_sh_vendor_statement"
        ).report_action(self)

    def action_send_vendor_statement(self):
        self.ensure_one()
        template = self.env.ref(
            "sh_account_statement.sh_vendor_statement_mail_template"
        )
        if template:
            mail = template.sudo().send_mail(self.id, force_send=True)
            mail_id = self.env["mail.mail"].sudo().browse(mail)
            if mail_id:
                self.env["sh.partner.mail.history"].sudo().create(
                    {
                        "name": "Vendor Account Statement",
                        "sh_statement_type": "vendor_statement",
                        "sh_current_date": fields.Datetime.now(),
                        "sh_partner_id": self.id,
                        "sh_mail_id": mail_id.id,
                        "sh_mail_status": mail_id.state,
                    }
                )

    def action_print_vendor_due_statement(self):
        return self.env.ref(
            "sh_account_statement.action_report_sh_vendor_due_statement"
        ).report_action(self)

    def action_send_vendor_due_statement(self):
        self.ensure_one()
        template = self.env.ref(
            "sh_account_statement.sh_vendor_due_statement_mail_template"
        )
        if template:
            mail = template.sudo().send_mail(self.id, force_send=True)
            mail_id = self.env["mail.mail"].sudo().browse(mail)
            if mail_id:
                self.env["sh.partner.mail.history"].sudo().create(
                    {
                        "name": "Vendor Account Overdue Statement",
                        "sh_statement_type": "vendor_overdue_statement",
                        "sh_current_date": fields.Datetime.now(),
                        "sh_partner_id": self.id,
                        "sh_mail_id": mail_id.id,
                        "sh_mail_status": mail_id.state,
                    }
                )

    def action_get_customer_statement(self):
        self.ensure_one()
        today = date.today()
        currQuarter = int((today.month - 1) / 3 + 1)
        if self.sh_date_filter!='custom':
            self.start_date=False
            self.end_date=False
        if self.sh_date_filter == 'this_month':
            self.start_date = date(today.year, today.month, 1)
            self.end_date  = date(today.year, today.month, calendar.mdays[today.month])

        if self.sh_date_filter == 'this_year':
            self.start_date = date(today.year, 1, 1)
            self.end_date = date(today.year, 12, 31)

        if self.sh_date_filter == 'last_month': 
            self.start_date = date(today.year, (today.month-1), 1)
            self.end_date = date(
                today.year, (today.month - 1), calendar.mdays[(today.month-1)])

        if self.sh_date_filter == 'last_year':
            self.start_date = date((today.year-1), 1, 1)
            self.end_date = date((today.year-1), 12, 31)

        if self.sh_date_filter == 'this_quarter':
            self.start_date = datetime(today.year, 3 * currQuarter - 2, 1)
            self.end_date = datetime(today.year, 3 * currQuarter + 1, 1) + timedelta(days=-1)
        
        if self.sh_date_filter == 'last_quarter':

            current_quar_start = datetime(today.year, 3 * currQuarter - 2, 1)

            self.start_date = datetime(today.year, current_quar_start.month, 1) + relativedelta(months=-3)
            self.end_date = current_quar_start + timedelta(days=-1)
            

        if self.customer_rank > 0 and self.start_date and self.end_date:

            self.sh_filter_customer_statement_ids.sudo().unlink()
            statement_lines = []

            account_id = self.property_account_receivable_id.id
            company_ids=[]
            if self.env.context and self.env.context.get('allowed_company_ids'):
                company_ids= self.env.context.get('allowed_company_ids')
            
            move_lines = self.env["account.move.line"].search(
                [
                    ("partner_id", "=", self.id),
                    ("date", "<", self.start_date),
                    ("account_id", "=", account_id),
                    ("parent_state", "=", "posted"),
                    ("company_id","in",company_ids)
                ]
            )

            balance = sum(move_lines.mapped("debit")) - sum(move_lines.mapped("credit"))

            statement_lines.append(
                (
                    0,
                    0,
                    {
                        "name": "Opening Balance",
                        "currency_id": move_lines[0].currency_id.id
                        if move_lines
                        else self.currency_id.id,
                        "sh_filter_balance": balance,
                    },
                )
            )
            if self.payment_state:
                moves = (
                    self.env["account.move"]
                    .sudo()
                    .search(
                        [
                            ("partner_id", "=", self.id),
                            ("move_type", "in", ["out_invoice", "out_refund"]),
                            ("invoice_date", ">=", self.start_date),
                            ("invoice_date", "<=", self.end_date),
                            ("state", "not in", ["draft", "cancel"]),
                            ('payment_state','=',self.payment_state),
                            ("company_id","in",company_ids)
                        ]
                    )
                )
            else:
                moves = (
                    self.env["account.move"]
                    .sudo()
                    .search(
                        [
                            ("partner_id", "=", self.id),
                            ("move_type", "in", ["out_invoice", "out_refund"]),
                            ("invoice_date", ">=", self.start_date),
                            ("invoice_date", "<=", self.end_date),
                            ("state", "not in", ["draft", "cancel"]),
                            ("company_id","in",company_ids)
                        ]
                    )
                )
            if moves:

                for move in moves:
                    statement_vals = {
                        "sh_account": self.property_account_receivable_id.name,
                        "name": move.name,
                        "currency_id": move.currency_id.id,
                        "sh_filter_invoice_date": move.invoice_date,
                        "sh_filter_due_date": move.invoice_date_due,
                    }
                    if move.move_type == "out_invoice":
                        statement_vals.update(
                            {
                                "sh_filter_amount": move.amount_total,
                                "sh_filter_paid_amount": move.amount_total
                                - move.amount_residual,
                                "sh_filter_balance": move.amount_total
                                - (move.amount_total - move.amount_residual),
                            }
                        )
                    elif move.move_type == "out_refund":
                        statement_vals.update(
                            {
                                "sh_filter_amount": move.amount_total*-1,
                                "sh_filter_paid_amount": (move.amount_total- move.amount_residual)*-1,
                                "sh_filter_balance": move.amount_residual*-1,
                            }
                        )
                    statement_lines.append((0, 0, statement_vals))

            advanced_payments_inbound = (
                self.env["account.payment"]
                .sudo()
                .search(
                    [
                        ("partner_id", "=", self.id),
                        ("date", ">=", self.start_date),
                        ("date", "<=", self.end_date),
                        ("state", "in", ["posted"]),
                        ("payment_type", "in", ["inbound"]),
                        ("partner_type", "in", ["customer"]),
                        ("company_id","in",company_ids)
                    ]
                )
            )
            if advanced_payments_inbound:
                for advance_payment in advanced_payments_inbound:
                    total_paid_amount = 0.0                   
                    
                    domain = [
                        ('account_id.account_type', 'in',('asset_receivable', 'liability_payable')),
                        ('parent_state', '=', 'posted'),
                        ('payment_id', '=', advance_payment.id),
                        ("company_id","in",company_ids)
                    ]
                    unpaid_move=self.env['account.move.line'].search(domain)
                    if unpaid_move:
                        unpaid_amount=sum(unpaid_move.mapped('amount_residual_currency'))
                        advance_payment_amount = advance_payment.amount
                        total_paid_amount = advance_payment.amount-abs(unpaid_amount)
                        # if advance_payment.reconciled_invoice_ids:
                        #     for invoice in advance_payment.reconciled_invoice_ids:

                        #         if (
                        #             invoice.invoice_date >= self.start_date
                        #             and invoice.invoice_date <= self.end_date
                        #         ):


                        if total_paid_amount < advance_payment_amount:
                            statement_vals = {
                                "sh_account": advance_payment.destination_account_id.name,
                                "name": advance_payment.name,
                                "currency_id": advance_payment.currency_id.id,
                                "sh_filter_invoice_date": advance_payment.date,
                                "sh_filter_amount": 0.0,
                                "sh_filter_paid_amount": unpaid_amount,
                                "sh_filter_balance": unpaid_amount,
                            }
                            statement_lines.append((0, 0, statement_vals))
                    else:
                        statement_vals = {
                            "sh_account": advance_payment.destination_account_id.name,
                            "name": advance_payment.name,
                            "currency_id": advance_payment.currency_id.id,
                            "sh_filter_invoice_date": advance_payment.date,
                            "sh_filter_amount": 0.0,
                            "sh_filter_paid_amount": advance_payment.amount,
                            "sh_filter_balance": -(advance_payment.amount),
                        }
                        statement_lines.append((0, 0, statement_vals))

            advanced_payments_outbound = (
                self.env["account.payment"]
                .sudo()
                .search(
                    [
                        ("partner_id", "=", self.id),
                        ("date", ">=", self.start_date),
                        ("date", "<=", self.end_date),
                        ("state", "in", ["posted"]),
                        ("payment_type", "in", ["outbound"]),
                        ("partner_type", "in", ["customer"]),
                        ("company_id","in",company_ids)
                    ]
                )
            )
            if advanced_payments_outbound:
                for advance_payment in advanced_payments_outbound:
                    total_paid_amount = 0.0
                    domain = [
                        ('account_id.account_type', 'in',('asset_receivable', 'liability_payable')),
                        ('parent_state', '=', 'posted'),
                        ('payment_id', '=', advance_payment.id),
                        ("company_id","in",company_ids)
                    ]
                    unpaid_move=self.env['account.move.line'].search(domain)
                    if unpaid_move:
                        unpaid_amount=sum(unpaid_move.mapped('amount_residual_currency'))
                        advance_payment_amount = advance_payment.amount
                    
                    
                    # if advance_payment.reconciled_invoice_ids:
                    #     for invoice in advance_payment.reconciled_invoice_ids:

                    #         if (
                    #             invoice.invoice_date >= self.start_date
                    #             and invoice.invoice_date <= self.end_date
                    #         ):

                    #             total_paid_amount += (
                    #                 invoice.amount_total - invoice.amount_residual
                    #             )
                        total_paid_amount=advance_payment_amount-unpaid_amount
                        if total_paid_amount < advance_payment_amount:
                            statement_vals = {
                                "sh_account": advance_payment.destination_account_id.name,
                                "name": advance_payment.name,
                                "currency_id": advance_payment.currency_id.id,
                                "sh_filter_invoice_date": advance_payment.date,
                                "sh_filter_amount": 0,
                                "sh_filter_paid_amount":unpaid_amount,
                                "sh_filter_balance": unpaid_amount,
                            }
                            statement_lines.append((0, 0, statement_vals))
                    else:
                        statement_vals = {
                            "sh_account": advance_payment.destination_account_id.name,
                            "name": advance_payment.name,
                            "currency_id": advance_payment.currency_id.id,
                            "sh_filter_invoice_date": advance_payment.date,
                            "sh_filter_amount": 0,
                            "sh_filter_paid_amount": unpaid_amount,
                            "sh_filter_balance": unpaid_amount,
                        }
                        statement_lines.append((0, 0, statement_vals))

            self.sh_filter_customer_statement_ids = statement_lines

    def action_print_filter_customer_statement(self):
        return self.env.ref(
            "sh_account_statement.action_report_sh_customer_filtered_statement"
        ).report_action(self)

    def action_send_filter_customer_statement(self):
        self.ensure_one()
        template = self.env.ref(
            "sh_account_statement.sh_customer_filter_statement_mail_template"
        )
        if template:
            mail = template.sudo().send_mail(self.id, force_send=True)
            mail_id = self.env["mail.mail"].sudo().browse(mail)
            if mail_id:
                self.env["sh.partner.mail.history"].sudo().create(
                    {
                        "name": "Customer Account Statement by Date",
                        "sh_statement_type": "customer_statement_filter",
                        "sh_current_date": fields.Datetime.now(),
                        "sh_partner_id": self.id,
                        "sh_mail_id": mail_id.id,
                        "sh_mail_status": mail_id.state,
                    }
                )

    def action_print_filter_customer_statement_xls(self):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            "font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        normal = xlwt.easyxf("font:bold True;align: horiz center;align: vert center")
        cyan_text = xlwt.easyxf(
            "font:bold True,color aqua;align: horiz center;align: vert center"
        )
        green_text = xlwt.easyxf(
            "font:bold True,color green;align: horiz center;align: vert center"
        )
        red_text = xlwt.easyxf(
            "font:bold True,color red;align: horiz center;align: vert center"
        )
        bold_center = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        date = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: vert center;align: horiz right;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        totals = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        worksheet = workbook.add_sheet(
            "Customer Statement Filter By Date", cell_overwrite_ok=True
        )

        worksheet.row(1).height = 380
        worksheet.row(2).height = 320
        worksheet.row(8).height = 400
        worksheet.col(2).width = 4800
        worksheet.col(3).width = 4800
        worksheet.col(4).width = 5500
        worksheet.col(5).width = 5500
        worksheet.col(6).width = 5500
        worksheet.col(0).width = 5500
        worksheet.col(1).width = 6000
        worksheet.write(1, 0, "Date From", date)
        if self.start_date:
            worksheet.write(1, 1, str(self.start_date), normal)
        worksheet.write(1, 2, "Date To", date)
        if self.end_date:
            worksheet.write(1, 3, str(self.end_date), normal)
        worksheet.write_merge(4, 5, 0, 6, self.name, heading_format)
        worksheet.write(8, 0, "Number", bold_center)
        worksheet.write(8, 1, "Account", bold_center)
        worksheet.write(8, 2, "Date", bold_center)
        worksheet.write(8, 3, "Due Date", bold_center)
        worksheet.write(8, 4, "Total Amount", bold_center)
        worksheet.write(8, 5, "Paid Amount", bold_center)
        worksheet.write(8, 6, "Balance", bold_center)

        total_amount = 0
        total_paid_amount = 0
        total_balance = 0
        k = 9

        if self.sh_filter_customer_statement_ids:
            for i in self.sh_filter_customer_statement_ids:
                for j in i:
                    worksheet.row(k).height = 350
                    if j.sh_filter_amount == j.sh_filter_balance:
                        if j.name == "Opening Balance":
                            worksheet.write(k, 0, j.name, green_text)
                            worksheet.write(k, 1, j.sh_account, green_text)
                            worksheet.write(
                                k, 2, str(j.sh_filter_invoice_date), green_text
                            )
                            if j.sh_filter_due_date:
                                worksheet.write(
                                    k, 3, str(j.sh_filter_due_date), green_text
                                )
                            else:
                                worksheet.write(k, 3, "", green_text)
                            worksheet.write(
                                k,
                                4,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_filter_amount)),
                                green_text,
                            )
                            worksheet.write(
                                k,
                                5,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_filter_paid_amount)),
                                green_text,
                            )
                            worksheet.write(
                                k,
                                6,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_filter_balance)),
                                green_text,
                            )
                        else:
                            worksheet.write(k, 0, j.name, cyan_text)
                            worksheet.write(k, 1, j.sh_account, cyan_text)
                            worksheet.write(
                                k, 2, str(j.sh_filter_invoice_date), cyan_text
                            )
                            if j.sh_filter_due_date:
                                worksheet.write(
                                    k, 3, str(j.sh_filter_due_date), cyan_text
                                )
                            else:
                                worksheet.write(k, 3, "", cyan_text)
                            worksheet.write(
                                k,
                                4,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_filter_amount)),
                                cyan_text,
                            )
                            worksheet.write(
                                k,
                                5,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_filter_paid_amount)),
                                cyan_text,
                            )
                            worksheet.write(
                                k,
                                6,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_filter_balance)),
                                cyan_text,
                            )
                    elif j.sh_filter_balance == 0:
                        worksheet.write(k, 0, j.name, green_text)
                        worksheet.write(k, 1, j.sh_account, green_text)
                        worksheet.write(k, 2, str(j.sh_filter_invoice_date), green_text)
                        if j.sh_filter_due_date:
                            worksheet.write(k, 3, str(j.sh_filter_due_date), green_text)
                        else:
                            worksheet.write(k, 3, "", green_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_filter_amount)),
                            green_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_filter_paid_amount)),
                            green_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_filter_balance)),
                            green_text,
                        )
                    else:
                        worksheet.write(k, 0, j.name, red_text)
                        worksheet.write(k, 1, j.sh_account, red_text)
                        worksheet.write(k, 2, str(j.sh_filter_invoice_date), red_text)
                        if j.sh_filter_due_date:
                            worksheet.write(k, 3, str(j.sh_filter_due_date), red_text)
                        else:
                            worksheet.write(k, 3, "", red_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_filter_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_filter_paid_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_filter_balance)),
                            red_text,
                        )
                    k = k + 1
                total_amount = total_amount + j.sh_filter_amount
                total_paid_amount = total_paid_amount + j.sh_filter_paid_amount
                total_balance = total_balance + j.sh_filter_balance
        if self.sh_filter_customer_statement_ids:
            worksheet.write(k, 4, str("{:.2f}".format(total_amount)), totals)
            worksheet.row(k).height = 350
            worksheet.write(k, 5, str("{:.2f}".format(total_paid_amount)), totals)
            worksheet.write(k, 6, str("{:.2f}".format(total_balance)), totals)

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env["ir.attachment"]
        attachment_vals = {
            "name": "Customer Statement Filter By Date.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search(
            [
                ("name", "=", "Customer Statement Filter By Date"),
                ("type", "=", "binary"),
                ("res_model", "=", "ir.ui.view"),
            ],
            limit=1,
        )
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)
        # TODO: make user error here
        if not attachment:
            raise UserError("There is no attachments...")

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "current",
        }

    def action_get_vendor_statement(self):
        self.ensure_one()

        today = date.today()
        currQuarter = int((today.month - 1) / 3 + 1)
        if self.sh_date_filter!='custom':
            self.start_date=False
            self.end_date=False
        if self.sh_date_filter == 'this_month':
            self.start_date = date(today.year, today.month, 1)
            self.end_date  = date(
                today.year, today.month, calendar.mdays[today.month])

        if self.sh_date_filter == 'this_year':
            self.start_date = date(today.year, 1, 1)
            self.end_date = date(today.year, 12, 31)

        if self.sh_date_filter == 'last_month': 
            self.start_date = date(today.year, (today.month-1), 1)
            self.end_date = date(
                today.year, (today.month - 1), calendar.mdays[(today.month-1)])

        if self.sh_date_filter == 'last_year':
            self.start_date = date((today.year-1), 1, 1)
            self.end_date = date((today.year-1), 12, 31)

        if self.sh_date_filter == 'this_quarter':
            self.start_date = datetime(today.year, 3 * currQuarter - 2, 1)
            self.end_date = datetime(today.year, 3 * currQuarter + 1, 1) + timedelta(days=-1)
        
        if self.sh_date_filter == 'last_quarter':

            current_quar_start = datetime(today.year, 3 * currQuarter - 2, 1)

            self.start_date = datetime(today.year, current_quar_start.month, 1) + relativedelta(months=-3)
            self.end_date = current_quar_start + timedelta(days=-1)


        if self.supplier_rank > 0 and self.start_date and self.end_date:

            statement_lines = []

            #########
            account_id = self.property_account_payable_id.id
            company_ids=[]
            if self.env.context and self.env.context.get('allowed_company_ids'):
                company_ids= self.env.context.get('allowed_company_ids')
            move_lines = self.env["account.move.line"].search(
                [
                    ("partner_id", "=", self.id),
                    ("date", "<", self.start_date),
                    ("account_id", "=", account_id),
                    ("parent_state", "=", "posted"),
                    ("company_id","in",company_ids)
                ]
            )

            balance = sum(move_lines.mapped("debit")) - sum(move_lines.mapped("credit"))

            statement_lines.append(
                (
                    0,
                    0,
                    {
                        "name": "Opening Balance",
                        "currency_id": move_lines[0].currency_id.id
                        if move_lines
                        else self.currency_id.id,
                        "sh_vendor_filter_balance": balance,
                    },
                )
            )
            #########
            if self.payment_state:
                moves = (
                    self.env["account.move"]
                    .sudo()
                    .search(
                        [
                            ("partner_id", "=", self.id),
                            ("move_type", "in", ["in_invoice", "in_refund"]),
                            ("invoice_date", ">=", self.start_date),
                            ("invoice_date", "<=", self.end_date),
                            ("state", "not in", ["draft", "cancel"]),
                            ('payment_state','=',self.payment_state),
                            ("company_id","in",company_ids)
                        ]
                    )
                )
            else:
                moves = (
                    self.env["account.move"]
                    .sudo()
                    .search(
                        [
                            ("partner_id", "=", self.id),
                            ("move_type", "in", ["in_invoice", "in_refund"]),
                            ("invoice_date", ">=", self.start_date),
                            ("invoice_date", "<=", self.end_date),
                            ("state", "not in", ["draft", "cancel"]),
                            ("company_id","in",company_ids)
                        ]
                    )
                )   
            self.sh_filter_vendor_statement_ids.unlink()
            if moves:

                for move in moves:
                    statement_vals = {
                        "sh_account": self.property_account_payable_id.name,
                        "name": move.name,
                        "currency_id": move.currency_id.id,
                        "sh_vendor_filter_invoice_date": move.invoice_date,
                        "sh_vendor_filter_due_date": move.invoice_date_due,
                    }
                    if move.move_type == "in_refund":
                        statement_vals.update(
                            {
                                "sh_vendor_filter_amount": move.amount_total,
                                "sh_vendor_filter_paid_amount": (move.amount_total- move.amount_residual),
                                "sh_vendor_filter_balance": move.amount_residual,
                            }
                        )
                    elif move.move_type == "in_invoice":
                        statement_vals.update(
                            {
                                "sh_vendor_filter_amount": move.amount_total*-1,
                                "sh_vendor_filter_paid_amount": (move.amount_total- move.amount_residual)*-1,
                                "sh_vendor_filter_balance": move.amount_residual*-1,
                            }
                        )
                    statement_lines.append((0, 0, statement_vals))

            advanced_payments_outbound = (
                self.env["account.payment"]
                .sudo()
                .search(
                    [
                        ("partner_id", "=", self.id),
                        ("date", ">=", self.start_date),
                        ("date", "<=", self.end_date),
                        ("state", "in", ["posted"]),
                        ("payment_type", "in", ["outbound"]),
                        ("partner_type", "in", ["supplier"]),
                        ("company_id","in",company_ids)
                    ]
                )
            )
            if advanced_payments_outbound:
                for advance_payment in advanced_payments_outbound:
                    total_paid_amount = 0.0
                    domain = [
                        ('account_id.account_type', 'in',('asset_receivable', 'liability_payable')),
                        ('parent_state', '=', 'posted'),
                        ('payment_id', '=', advance_payment.id),
                        ("company_id","in",company_ids)
                    ]
                    unpaid_move=self.env['account.move.line'].search(domain)
                    if unpaid_move:
                        unpaid_amount=sum(unpaid_move.mapped('amount_residual_currency'))
                        advance_payment_amount = advance_payment.amount
                        total_paid_amount = advance_payment.amount-abs(unpaid_amount)
                    # if advance_payment.reconciled_bill_ids:
                    #     advance_payment_amount = advance_payment.amount
                    #     for invoice in advance_payment.reconciled_bill_ids:
                    #         if (
                    #             invoice.invoice_date >= self.start_date
                    #             and invoice.invoice_date <= self.end_date
                    #         ):

                    #             total_paid_amount += (
                    #                 invoice.amount_total - invoice.amount_residual
                    #             )

                        if total_paid_amount < advance_payment_amount:
                            statement_vals = {
                                "sh_account": advance_payment.destination_account_id.name,
                                "name": advance_payment.name,
                                "currency_id": advance_payment.currency_id.id,
                                "sh_vendor_filter_invoice_date": advance_payment.date,
                                "sh_vendor_filter_amount": 0,
                                "sh_vendor_filter_paid_amount": unpaid_amount,
                                "sh_vendor_filter_balance": unpaid_amount,
                            }
                            statement_lines.append((0, 0, statement_vals))
                    else:
                        statement_vals = {
                            "sh_account": advance_payment.destination_account_id.name,
                            "name": advance_payment.name,
                            "currency_id": advance_payment.currency_id.id,
                            "sh_vendor_filter_invoice_date": advance_payment.date,
                            "sh_vendor_filter_amount": 0,
                            "sh_vendor_filter_paid_amount": advance_payment.amount,
                            "sh_vendor_filter_balance": advance_payment.amount,
                        }
                        statement_lines.append((0, 0, statement_vals))

            advanced_payments_inbound = (
                self.env["account.payment"]
                .sudo()
                .search(
                    [
                        ("partner_id", "=", self.id),
                        ("date", ">=", self.start_date),
                        ("date", "<=", self.end_date),
                        ("state", "in", ["posted"]),
                        ("payment_type", "in", ["inbound"]),
                        ("partner_type", "in", ["supplier"]),
                        ("company_id","in",company_ids)
                    ]
                )
            )
            if advanced_payments_inbound:
                for advance_payment in advanced_payments_inbound:
                    total_paid_amount = 0.0
                    domain = [
                        ('account_id.account_type', 'in',('asset_receivable', 'liability_payable')),
                        ('parent_state', '=', 'posted'),
                        ('payment_id', '=', advance_payment.id),
                        ("company_id","in",company_ids)
                    ]
                    unpaid_move=self.env['account.move.line'].search(domain)
                    if unpaid_move:
                        unpaid_amount=sum(unpaid_move.mapped('amount_residual_currency'))
                        advance_payment_amount = advance_payment.amount
                        total_paid_amount = advance_payment.amount-abs(unpaid_amount)
                    # if advance_payment.reconciled_bill_ids:
                    #     advance_payment_amount = advance_payment.amount
                    #     for invoice in advance_payment.reconciled_bill_ids:
                    #         if (
                    #             invoice.invoice_date >= self.start_date
                    #             and invoice.invoice_date <= self.end_date
                    #         ):

                    #             total_paid_amount += (
                    #                 invoice.amount_total - invoice.amount_residual
                    #             )
                        if total_paid_amount < advance_payment_amount:
                            statement_vals = {
                                "sh_account": advance_payment.destination_account_id.name,
                                "name": advance_payment.name,
                                "currency_id": advance_payment.currency_id.id,
                                "sh_vendor_filter_invoice_date": advance_payment.date,
                                "sh_vendor_filter_amount": 0.0,
                                "sh_vendor_filter_paid_amount":unpaid_amount,
                                "sh_vendor_filter_balance": unpaid_amount,
                            }
                            statement_lines.append((0, 0, statement_vals))
                    else:
                        statement_vals = {
                            "sh_account": advance_payment.destination_account_id.name,
                            "name": advance_payment.name,
                            "currency_id": advance_payment.currency_id.id,
                            "sh_vendor_filter_invoice_date": advance_payment.date,
                            "sh_vendor_filter_amount": 0.0,
                            "sh_vendor_filter_paid_amount": advance_payment.amount,
                            "sh_vendor_filter_balance": -(advance_payment.amount),
                        }
                        statement_lines.append((0, 0, statement_vals))

            self.sh_filter_vendor_statement_ids = statement_lines

    def action_print_filter_vendor_statement(self):
        return self.env.ref(
            "sh_account_statement.action_report_sh_vendor_filtered_statement"
        ).report_action(self)

    def action_send_filter_vendor_statement(self):
        self.ensure_one()
        template = self.env.ref(
            "sh_account_statement.sh_vendor_filter_statement_mail_template"
        )
        if template:
            mail = template.sudo().send_mail(self.id, force_send=True)
            mail_id = self.env["mail.mail"].sudo().browse(mail)
            if mail_id:
                self.env["sh.partner.mail.history"].sudo().create(
                    {
                        "name": "Vendor Account Statement by Date",
                        "sh_statement_type": "vendor_statement_filter",
                        "sh_current_date": fields.Datetime.now(),
                        "sh_partner_id": self.id,
                        "sh_mail_id": mail_id.id,
                        "sh_mail_status": mail_id.state,
                    }
                )

    def action_view_partner_history(self):
        self.ensure_one()
        return {
            "name": "Mail Log History",
            "type": "ir.actions.act_window",
            "res_model": "sh.partner.mail.history",
            "view_mode": "tree,form",
            "domain": [("sh_partner_id", "=", self.id)],
            "target": "current",
        }

    @api.model
    def _run_auto_send_statements(self):
        temp = []
        statement_partners_ids = self.env["sh.statement.config"].sudo().search([])
        if statement_partners_ids:
            for statement in statement_partners_ids:
                for partner in statement.sh_customer_partner_ids:
                    if partner.id not in temp:
                        temp.append(partner.id)
                for partner in statement.sh_vendor_partner_ids:
                    if partner.id not in temp:
                        temp.append(partner.id)
        partner_ids = self.env["res.partner"].sudo().search([("id", "not in", temp)])

        for partner in partner_ids:
            try:
                # for customer
                if partner.customer_rank > 0:
                    # for statement
                    if not partner.sh_dont_send_statement_auto:
                        if (
                            self.env.company.sh_customer_statement_auto_send
                            and partner.sh_customer_statement_ids
                        ):
                            if self.env.company.filter_only_unpaid_and_send_that and not partner.sh_customer_statement_ids.filtered(lambda x:x.sh_filter_balance > 0):
                                return
                            
                            if self.env.company.sh_customer_statement_action == "daily":
                                if self.env.company.sh_cus_daily_statement_template_id:
                                    mail = self.env.company.sh_cus_daily_statement_template_id.sudo().send_mail(
                                        partner.id, force_send=True
                                    )
                                    mail_id = self.env["mail.mail"].sudo().browse(mail)
                                    if (
                                        mail_id
                                        and self.env.company.sh_cust_create_log_history
                                    ):
                                        self.env[
                                            "sh.partner.mail.history"
                                        ].sudo().create(
                                            {
                                                "name": "Customer Account Statement",
                                                "sh_statement_type": "customer_statement",
                                                "sh_current_date": fields.Datetime.now(),
                                                "sh_partner_id": partner.id,
                                                "sh_mail_id": mail_id.id,
                                                "sh_mail_status": mail_id.state,
                                            }
                                        )
                            elif (
                                self.env.company.sh_customer_statement_action
                                == "weekly"
                            ):
                                today = fields.Date.today().weekday()
                                if int(self.env.company.sh_cust_week_day) == today:
                                    if (
                                        self.env.company.sh_cust_weekly_statement_template_id
                                    ):
                                        mail = self.env.company.sh_cust_weekly_statement_template_id.sudo().send_mail(
                                            partner.id, force_send=True
                                        )
                                        mail_id = (
                                            self.env["mail.mail"].sudo().browse(mail)
                                        )
                                        if (
                                            mail_id
                                            and self.env.company.sh_cust_create_log_history
                                        ):
                                            self.env[
                                                "sh.partner.mail.history"
                                            ].sudo().create(
                                                {
                                                    "name": "Customer Account Statement",
                                                    "sh_statement_type": "customer_statement",
                                                    "sh_current_date": fields.Datetime.now(),
                                                    "sh_partner_id": partner.id,
                                                    "sh_mail_id": mail_id.id,
                                                    "sh_mail_status": mail_id.state,
                                                }
                                            )
                            elif (
                                self.env.company.sh_customer_statement_action
                                == "monthly"
                            ):
                                monthly_day = self.env.company.sh_cust_monthly_date
                                today = fields.Date.today()
                                today_date = today.day
                                if self.env.company.sh_cust_monthly_end:
                                    last_day = calendar.monthrange(
                                        today.year, today.month
                                    )[1]
                                    if today_date == last_day:
                                        if self.env.company.sh_cust_monthly_template_id:
                                            mail = self.env.company.sh_cust_monthly_template_id.sudo().send_mail(
                                                partner.id, force_send=True
                                            )
                                            mail_id = (
                                                self.env["mail.mail"]
                                                .sudo()
                                                .browse(mail)
                                            )
                                            if (
                                                mail_id
                                                and self.env.company.sh_cust_create_log_history
                                            ):
                                                self.env[
                                                    "sh.partner.mail.history"
                                                ].sudo().create(
                                                    {
                                                        "name": "Customer Account Statement",
                                                        "sh_statement_type": "customer_statement",
                                                        "sh_current_date": fields.Datetime.now(),
                                                        "sh_partner_id": partner.id,
                                                        "sh_mail_id": mail_id.id,
                                                        "sh_mail_status": mail_id.state,
                                                    }
                                                )
                                else:
                                    if today_date == monthly_day:
                                        if self.env.company.sh_cust_monthly_template_id:
                                            mail = self.env.company.sh_cust_monthly_template_id.sudo().send_mail(
                                                partner.id, force_send=True
                                            )
                                            mail_id = (
                                                self.env["mail.mail"]
                                                .sudo()
                                                .browse(mail)
                                            )
                                            if (
                                                mail_id
                                                and self.env.company.sh_cust_create_log_history
                                            ):
                                                self.env[
                                                    "sh.partner.mail.history"
                                                ].sudo().create(
                                                    {
                                                        "name": "Customer Account Statement",
                                                        "sh_statement_type": "customer_statement",
                                                        "sh_current_date": fields.Datetime.now(),
                                                        "sh_partner_id": partner.id,
                                                        "sh_mail_id": mail_id.id,
                                                        "sh_mail_status": mail_id.state,
                                                    }
                                                )
                            elif (
                                self.env.company.sh_customer_statement_action
                                == "yearly"
                            ):
                                today = fields.Date.today()
                                today_date = today.day
                                today_month = today.strftime("%B").lower()
                                if (
                                    self.env.company.sh_cust_yearly_date == today_date
                                    and self.env.company.sh_cust_yearly_month
                                    == today_month
                                ):
                                    if self.env.company.sh_cust_yearly_template_id:
                                        mail = self.env.company.sh_cust_yearly_template_id.sudo().send_mail(
                                            partner.id, force_send=True
                                        )
                                        mail_id = (
                                            self.env["mail.mail"].sudo().browse(mail)
                                        )
                                        if (
                                            mail_id
                                            and self.env.company.sh_cust_create_log_history
                                        ):
                                            self.env[
                                                "sh.partner.mail.history"
                                            ].sudo().create(
                                                {
                                                    "name": "Customer Account Statement",
                                                    "sh_statement_type": "customer_statement",
                                                    "sh_current_date": fields.Datetime.now(),
                                                    "sh_partner_id": partner.id,
                                                    "sh_mail_id": mail_id.id,
                                                    "sh_mail_status": mail_id.state,
                                                }
                                            )
                    # for overdue statement
                    if not partner.sh_dont_send_due_statement_auto:
                        if (
                            self.env.company.sh_customer_due_statement_auto_send
                            and partner.sh_customer_due_statement_ids
                        ):
                            if self.env.company.filter_only_unpaid_and_send_that and not partner.sh_customer_due_statement_ids.filtered(lambda x:x.sh_filter_balance > 0):
                                return
                            if (
                                self.env.company.sh_customer_due_statement_action
                                == "daily"
                            ):
                                if (
                                    self.env.company.sh_cus_due_daily_statement_template_id
                                ):
                                    mail = self.env.company.sh_cus_due_daily_statement_template_id.sudo().send_mail(
                                        partner.id, force_send=True
                                    )
                                    mail_id = self.env["mail.mail"].sudo().browse(mail)
                                    if (
                                        mail_id
                                        and self.env.company.sh_cust_due_create_log_history
                                    ):
                                        self.env[
                                            "sh.partner.mail.history"
                                        ].sudo().create(
                                            {
                                                "name": "Customer Account Overdue Statement",
                                                "sh_statement_type": "customer_overdue_statement",
                                                "sh_current_date": fields.Datetime.now(),
                                                "sh_partner_id": partner.id,
                                                "sh_mail_id": mail_id.id,
                                                "sh_mail_status": mail_id.state,
                                            }
                                        )
                            elif (
                                self.env.company.sh_customer_due_statement_action
                                == "weekly"
                            ):
                                today = fields.Date.today().weekday()
                                if int(self.env.company.sh_cust_due_week_day) == today:
                                    if (
                                        self.env.company.sh_cust_due_weekly_statement_template_id
                                    ):
                                        mail = self.env.company.sh_cust_due_weekly_statement_template_id.sudo().send_mail(
                                            partner.id, force_send=True
                                        )
                                        mail_id = (
                                            self.env["mail.mail"].sudo().browse(mail)
                                        )
                                        if (
                                            mail_id
                                            and self.env.company.sh_cust_due_create_log_history
                                        ):
                                            self.env[
                                                "sh.partner.mail.history"
                                            ].sudo().create(
                                                {
                                                    "name": "Customer Account Overdue Statement",
                                                    "sh_statement_type": "customer_overdue_statement",
                                                    "sh_current_date": fields.Datetime.now(),
                                                    "sh_partner_id": partner.id,
                                                    "sh_mail_id": mail_id.id,
                                                    "sh_mail_status": mail_id.state,
                                                }
                                            )
                            elif (
                                self.env.company.sh_customer_due_statement_action
                                == "monthly"
                            ):
                                monthly_day = self.env.company.sh_cust_due_monthly_date
                                today = fields.Date.today()
                                today_date = today.day
                                if self.env.company.sh_cust_due_monthly_end:
                                    last_day = calendar.monthrange(
                                        today.year, today.month
                                    )[1]
                                    if today_date == last_day:
                                        if (
                                            self.env.company.sh_cust_due_monthly_template_id
                                        ):
                                            mail = self.env.company.sh_cust_due_monthly_template_id.sudo().send_mail(
                                                partner.id, force_send=True
                                            )
                                            mail_id = (
                                                self.env["mail.mail"]
                                                .sudo()
                                                .browse(mail)
                                            )
                                            if (
                                                mail_id
                                                and self.env.company.sh_cust_due_create_log_history
                                            ):
                                                self.env[
                                                    "sh.partner.mail.history"
                                                ].sudo().create(
                                                    {
                                                        "name": "Customer Account Overdue Statement",
                                                        "sh_statement_type": "customer_overdue_statement",
                                                        "sh_current_date": fields.Datetime.now(),
                                                        "sh_partner_id": partner.id,
                                                        "sh_mail_id": mail_id.id,
                                                        "sh_mail_status": mail_id.state,
                                                    }
                                                )
                                else:
                                    if today_date == monthly_day:
                                        if (
                                            self.env.company.sh_cust_due_monthly_template_id
                                        ):
                                            mail = self.env.company.sh_cust_due_monthly_template_id.sudo().send_mail(
                                                partner.id, force_send=True
                                            )
                                            mail_id = (
                                                self.env["mail.mail"]
                                                .sudo()
                                                .browse(mail)
                                            )
                                            if (
                                                mail_id
                                                and self.env.company.sh_cust_due_create_log_history
                                            ):
                                                self.env[
                                                    "sh.partner.mail.history"
                                                ].sudo().create(
                                                    {
                                                        "name": "Customer Account Overdue Statement",
                                                        "sh_statement_type": "customer_overdue_statement",
                                                        "sh_current_date": fields.Datetime.now(),
                                                        "sh_partner_id": partner.id,
                                                        "sh_mail_id": mail_id.id,
                                                        "sh_mail_status": mail_id.state,
                                                    }
                                                )

                            elif (
                                self.env.company.sh_customer_due_statement_action
                                == "yearly"
                            ):
                                today = fields.Date.today()
                                today_date = today.day
                                today_month = today.strftime("%B").lower()
                                if (
                                    self.env.company.sh_cust_due_yearly_date
                                    == today_date
                                    and self.env.company.sh_cust_due_yearly_month
                                    == today_month
                                ):
                                    if self.env.company.sh_cust_due_yearly_template_id:
                                        mail = self.env.company.sh_cust_due_yearly_template_id.sudo().send_mail(
                                            partner.id, force_send=True
                                        )
                                        mail_id = (
                                            self.env["mail.mail"].sudo().browse(mail)
                                        )
                                        if (
                                            mail_id
                                            and self.env.company.sh_cust_due_create_log_history
                                        ):
                                            self.env[
                                                "sh.partner.mail.history"
                                            ].sudo().create(
                                                {
                                                    "name": "Customer Account Overdue Statement",
                                                    "sh_statement_type": "customer_overdue_statement",
                                                    "sh_current_date": fields.Datetime.now(),
                                                    "sh_partner_id": partner.id,
                                                    "sh_mail_id": mail_id.id,
                                                    "sh_mail_status": mail_id.state,
                                                }
                                            )
                # for Vendor
                if partner.supplier_rank > 0:
                    # for statement
                    if not partner.sh_dont_send_statement_auto:
                        if (
                            self.env.company.sh_vendor_statement_auto_send
                            and partner.sh_vendor_statement_ids
                        ):
                            if self.env.company.filter_only_unpaid_bill_and_send_that and not partner.sh_vendor_statement_ids.filtered(lambda x:x.sh_filter_balance > 0):
                                return
                            if self.env.company.sh_vendor_statement_action == "daily":
                                if self.env.company.sh_vend_daily_statement_template_id:
                                    mail = self.env.company.sh_vend_daily_statement_template_id.sudo().send_mail(
                                        partner.id, force_send=True
                                    )
                                    mail_id = self.env["mail.mail"].sudo().browse(mail)
                                    if (
                                        mail_id
                                        and self.env.company.sh_vend_create_log_history
                                    ):
                                        self.env[
                                            "sh.partner.mail.history"
                                        ].sudo().create(
                                            {
                                                "name": "Vendor Account Statement",
                                                "sh_statement_type": "vendor_statement",
                                                "sh_current_date": fields.Datetime.now(),
                                                "sh_partner_id": partner.id,
                                                "sh_mail_id": mail_id.id,
                                                "sh_mail_status": mail_id.state,
                                            }
                                        )
                            elif (
                                self.env.company.sh_vendor_statement_action == "weekly"
                            ):
                                today = fields.Date.today().weekday()
                                if int(self.env.company.sh_vend_week_day) == today:
                                    if (
                                        self.env.company.sh_vend_weekly_statement_template_id
                                    ):
                                        mail = self.env.company.sh_vend_weekly_statement_template_id.sudo().send_mail(
                                            partner.id, force_send=True
                                        )
                                        mail_id = (
                                            self.env["mail.mail"].sudo().browse(mail)
                                        )
                                        if (
                                            mail_id
                                            and self.env.company.sh_vend_create_log_history
                                        ):
                                            self.env[
                                                "sh.partner.mail.history"
                                            ].sudo().create(
                                                {
                                                    "name": "Vendor Account Statement",
                                                    "sh_statement_type": "vendor_statement",
                                                    "sh_current_date": fields.Datetime.now(),
                                                    "sh_partner_id": partner.id,
                                                    "sh_mail_id": mail_id.id,
                                                    "sh_mail_status": mail_id.state,
                                                }
                                            )
                            elif (
                                self.env.company.sh_vendor_statement_action == "monthly"
                            ):
                                monthly_day = self.env.company.sh_vend_monthly_date
                                today = fields.Date.today()
                                today_date = today.day
                                if self.env.company.sh_vend_monthly_end:
                                    last_day = calendar.monthrange(
                                        today.year, today.month
                                    )[1]
                                    if today_date == last_day:
                                        if self.env.company.sh_vend_monthly_template_id:
                                            mail = self.env.company.sh_vend_monthly_template_id.sudo().send_mail(
                                                partner.id, force_send=True
                                            )
                                            mail_id = (
                                                self.env["mail.mail"]
                                                .sudo()
                                                .browse(mail)
                                            )
                                            if (
                                                mail_id
                                                and self.env.company.sh_vend_create_log_history
                                            ):
                                                self.env[
                                                    "sh.partner.mail.history"
                                                ].sudo().create(
                                                    {
                                                        "name": "Vendor Account Statement",
                                                        "sh_statement_type": "vendor_statement",
                                                        "sh_current_date": fields.Datetime.now(),
                                                        "sh_partner_id": partner.id,
                                                        "sh_mail_id": mail_id.id,
                                                        "sh_mail_status": mail_id.state,
                                                    }
                                                )
                                else:
                                    if today_date == monthly_day:
                                        if self.env.company.sh_vend_monthly_template_id:
                                            mail = self.env.company.sh_vend_monthly_template_id.sudo().send_mail(
                                                partner.id, force_send=True
                                            )
                                            mail_id = (
                                                self.env["mail.mail"]
                                                .sudo()
                                                .browse(mail)
                                            )
                                            if (
                                                mail_id
                                                and self.env.company.sh_vend_create_log_history
                                            ):
                                                self.env[
                                                    "sh.partner.mail.history"
                                                ].sudo().create(
                                                    {
                                                        "name": "Vendor Account Statement",
                                                        "sh_statement_type": "vendor_statement",
                                                        "sh_current_date": fields.Datetime.now(),
                                                        "sh_partner_id": partner.id,
                                                        "sh_mail_id": mail_id.id,
                                                        "sh_mail_status": mail_id.state,
                                                    }
                                                )
                            elif (
                                self.env.company.sh_vendor_statement_action == "yearly"
                            ):
                                today = fields.Date.today()
                                today_date = today.day
                                today_month = today.strftime("%B").lower()
                                if (
                                    self.env.company.sh_vend_yearly_date == today_date
                                    and self.env.company.sh_vend_yearly_month
                                    == today_month
                                ):
                                    if self.env.company.sh_vend_yearly_template_id:
                                        mail = self.env.company.sh_vend_yearly_template_id.sudo().send_mail(
                                            partner.id, force_send=True
                                        )
                                        mail_id = (
                                            self.env["mail.mail"].sudo().browse(mail)
                                        )
                                        if (
                                            mail_id
                                            and self.env.company.sh_vend_create_log_history
                                        ):
                                            self.env[
                                                "sh.partner.mail.history"
                                            ].sudo().create(
                                                {
                                                    "name": "Vendor Account Statement",
                                                    "sh_statement_type": "vendor_statement",
                                                    "sh_current_date": fields.Datetime.now(),
                                                    "sh_partner_id": partner.id,
                                                    "sh_mail_id": mail_id.id,
                                                    "sh_mail_status": mail_id.state,
                                                }
                                            )
                    # for overdue statement
                    if not partner.sh_dont_send_due_statement_auto:
                        if (
                            self.env.company.sh_vendor_due_statement_auto_send
                            and partner.sh_vendor_due_statement_ids
                        ):
                            if self.env.company.filter_only_unpaid_bill_and_send_that and not partner.sh_vendor_due_statement_ids.filtered(lambda x:x.sh_filter_balance > 0):
                                return
                            
                            if (
                                self.env.company.sh_vendor_due_statement_action
                                == "daily"
                            ):
                                if (
                                    self.env.company.sh_vend_due_daily_statement_template_id
                                ):
                                    mail = self.env.company.sh_vend_due_daily_statement_template_id.sudo().send_mail(
                                        partner.id, force_send=True
                                    )
                                    mail_id = self.env["mail.mail"].sudo().browse(mail)
                                    if (
                                        mail_id
                                        and self.env.company.sh_vend_due_create_log_history
                                    ):
                                        self.env[
                                            "sh.partner.mail.history"
                                        ].sudo().create(
                                            {
                                                "name": "Vendor Account Overdue Statement",
                                                "sh_statement_type": "vendor_overdue_statement",
                                                "sh_current_date": fields.Datetime.now(),
                                                "sh_partner_id": partner.id,
                                                "sh_mail_id": mail_id.id,
                                                "sh_mail_status": mail_id.state,
                                            }
                                        )
                            elif (
                                self.env.company.sh_vendor_due_statement_action
                                == "weekly"
                            ):
                                today = fields.Date.today().weekday()
                                if int(self.env.company.sh_vend_due_week_day) == today:
                                    if (
                                        self.env.company.sh_vend_due_weekly_statement_template_id
                                    ):
                                        mail = self.env.company.sh_vend_due_weekly_statement_template_id.sudo().send_mail(
                                            partner.id, force_send=True
                                        )
                                        mail_id = (
                                            self.env["mail.mail"].sudo().browse(mail)
                                        )
                                        if (
                                            mail_id
                                            and self.env.company.sh_vend_due_create_log_history
                                        ):
                                            self.env[
                                                "sh.partner.mail.history"
                                            ].sudo().create(
                                                {
                                                    "name": "Vendor Account Overdue Statement",
                                                    "sh_statement_type": "vendor_overdue_statement",
                                                    "sh_current_date": fields.Datetime.now(),
                                                    "sh_partner_id": partner.id,
                                                    "sh_mail_id": mail_id.id,
                                                    "sh_mail_status": mail_id.state,
                                                }
                                            )
                            elif (
                                self.env.company.sh_vendor_due_statement_action
                                == "monthly"
                            ):
                                monthly_day = self.env.company.sh_vend_due_monthly_date
                                today = fields.Date.today()
                                today_date = today.day
                                if self.env.company.sh_vend_due_monthly_end:
                                    last_day = calendar.monthrange(
                                        today.year, today.month
                                    )[1]
                                    if today_date == last_day:
                                        if (
                                            self.env.company.sh_vend_due_monthly_template_id
                                        ):
                                            mail = self.env.company.sh_vend_due_monthly_template_id.sudo().send_mail(
                                                partner.id, force_send=True
                                            )
                                            mail_id = (
                                                self.env["mail.mail"]
                                                .sudo()
                                                .browse(mail)
                                            )
                                            if (
                                                mail_id
                                                and self.env.company.sh_vend_due_create_log_history
                                            ):
                                                self.env[
                                                    "sh.partner.mail.history"
                                                ].sudo().create(
                                                    {
                                                        "name": "Vendor Account Overdue Statement",
                                                        "sh_statement_type": "vendor_overdue_statement",
                                                        "sh_current_date": fields.Datetime.now(),
                                                        "sh_partner_id": partner.id,
                                                        "sh_mail_id": mail_id.id,
                                                        "sh_mail_status": mail_id.state,
                                                    }
                                                )
                                else:
                                    if today_date == monthly_day:
                                        if (
                                            self.env.company.sh_vend_due_monthly_template_id
                                        ):
                                            mail = self.env.company.sh_vend_due_monthly_template_id.sudo().send_mail(
                                                partner.id, force_send=True
                                            )
                                            mail_id = (
                                                self.env["mail.mail"]
                                                .sudo()
                                                .browse(mail)
                                            )
                                            if (
                                                mail_id
                                                and self.env.company.sh_vend_due_create_log_history
                                            ):
                                                self.env[
                                                    "sh.partner.mail.history"
                                                ].sudo().create(
                                                    {
                                                        "name": "Vendor Account Overdue Statement",
                                                        "sh_statement_type": "vendor_overdue_statement",
                                                        "sh_current_date": fields.Datetime.now(),
                                                        "sh_partner_id": partner.id,
                                                        "sh_mail_id": mail_id.id,
                                                        "sh_mail_status": mail_id.state,
                                                    }
                                                )
                            elif (
                                self.env.company.sh_vendor_due_statement_action
                                == "yearly"
                            ):
                                today = fields.Date.today()
                                today_date = today.day
                                today_month = today.strftime("%B").lower()
                                if (
                                    self.env.company.sh_vend_due_yearly_date
                                    == today_date
                                    and self.env.company.sh_vend_due_yearly_month
                                    == today_month
                                ):
                                    if self.env.company.sh_vend_due_yearly_template_id:
                                        mail = self.env.company.sh_vend_due_yearly_template_id.sudo().send_mail(
                                            partner.id, force_send=True
                                        )
                                        mail_id = (
                                            self.env["mail.mail"].sudo().browse(mail)
                                        )
                                        if (
                                            mail_id
                                            and self.env.company.sh_vend_due_create_log_history
                                        ):
                                            self.env[
                                                "sh.partner.mail.history"
                                            ].sudo().create(
                                                {
                                                    "name": "Vendor Account Overdue Statement",
                                                    "sh_statement_type": "vendor_overdue_statement",
                                                    "sh_current_date": fields.Datetime.now(),
                                                    "sh_partner_id": partner.id,
                                                    "sh_mail_id": mail_id.id,
                                                    "sh_mail_status": mail_id.state,
                                                }
                                            )
            except Exception as e:
                _logger.error("%s", e)

    def action_print_filter_vendor_statement_xls(self):

        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            "font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        normal = xlwt.easyxf("font:bold True;align: horiz center;align: vert center")
        cyan_text = xlwt.easyxf(
            "font:bold True,color aqua;align: horiz center;align: vert center"
        )
        green_text = xlwt.easyxf(
            "font:bold True,color green;align: horiz center;align: vert center"
        )
        red_text = xlwt.easyxf(
            "font:bold True,color red;align: horiz center;align: vert center"
        )
        bold_center = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        date = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: vert center;align: horiz right;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        totals = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        worksheet = workbook.add_sheet(
            "Vendor Statement Filter By Date", cell_overwrite_ok=True
        )

        worksheet.col(1).width = 3000
        worksheet.row(1).height = 380
        worksheet.row(2).height = 320
        worksheet.row(8).height = 400
        worksheet.col(1).width = 3000
        worksheet.col(2).width = 4800
        worksheet.col(3).width = 4800
        worksheet.col(4).width = 5500
        worksheet.col(5).width = 5500
        worksheet.col(6).width = 5500
        worksheet.col(0).width = 5500
        worksheet.col(1).width = 6000
        worksheet.write(1, 0, "Date From", date)
        if self.start_date:
            worksheet.write(1, 1, str(self.start_date), normal)
        worksheet.write(1, 2, "Date To", date)
        if self.end_date:
            worksheet.write(1, 3, str(self.end_date), normal)
        worksheet.write_merge(4, 5, 0, 6, self.name, heading_format)
        worksheet.write(8, 0, "Number", bold_center)
        worksheet.write(8, 1, "Account", bold_center)
        worksheet.write(8, 2, "Date", bold_center)
        worksheet.write(8, 3, "Due Date", bold_center)
        worksheet.write(8, 4, "Total Amount", bold_center)
        worksheet.write(8, 5, "Paid Amount", bold_center)
        worksheet.write(8, 6, "Balance", bold_center)

        total_amount = 0
        total_paid_amount = 0
        total_balance = 0
        k = 9

        if self.sh_filter_vendor_statement_ids:
            for i in self.sh_filter_vendor_statement_ids:
                for j in i:
                    worksheet.row(k).height = 350
                    if j.sh_vendor_filter_amount == j.sh_vendor_filter_balance:
                        if j.name == "Opening Balance":
                            worksheet.write(k, 0, j.name, green_text)
                            worksheet.write(k, 1, j.sh_account, green_text)
                            worksheet.write(
                                k, 2, str(j.sh_vendor_filter_invoice_date), green_text
                            )
                            if j.sh_vendor_filter_due_date:
                                worksheet.write(
                                    k, 3, str(j.sh_vendor_filter_due_date), green_text
                                )
                            else:
                                worksheet.write(k, 3, "", green_text)
                            worksheet.write(
                                k,
                                4,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_vendor_filter_amount)),
                                green_text,
                            )
                            worksheet.write(
                                k,
                                5,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_vendor_filter_paid_amount)),
                                green_text,
                            )
                            worksheet.write(
                                k,
                                6,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_vendor_filter_balance)),
                                green_text,
                            )
                        else:
                            worksheet.write(k, 0, j.name, cyan_text)
                            worksheet.write(k, 1, j.sh_account, cyan_text)
                            worksheet.write(
                                k, 2, str(j.sh_vendor_filter_invoice_date), cyan_text
                            )
                            if j.sh_vendor_filter_due_date:
                                worksheet.write(
                                    k, 3, str(j.sh_vendor_filter_due_date), cyan_text
                                )
                            else:
                                worksheet.write(k, 3, "", cyan_text)
                            worksheet.write(
                                k,
                                4,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_vendor_filter_amount)),
                                cyan_text,
                            )
                            worksheet.write(
                                k,
                                5,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_vendor_filter_paid_amount)),
                                cyan_text,
                            )
                            worksheet.write(
                                k,
                                6,
                                str(i.currency_id.symbol)
                                + str("{:.2f}".format(j.sh_vendor_filter_balance)),
                                cyan_text,
                            )
                    elif j.sh_vendor_filter_balance == 0:
                        worksheet.write(k, 0, j.name, green_text)
                        worksheet.write(k, 1, j.sh_account, green_text)
                        worksheet.write(
                            k, 2, str(j.sh_vendor_filter_invoice_date), green_text
                        )
                        if j.sh_vendor_filter_due_date:
                            worksheet.write(
                                k, 3, str(j.sh_vendor_filter_due_date), green_text
                            )
                        else:
                            worksheet.write(k, 3, "", green_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_filter_amount)),
                            green_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_filter_paid_amount)),
                            green_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_filter_balance)),
                            green_text,
                        )
                    else:
                        worksheet.write(k, 0, j.name, red_text)
                        worksheet.write(k, 1, j.sh_account, red_text)
                        worksheet.write(
                            k, 2, str(j.sh_vendor_filter_invoice_date), red_text
                        )
                        if j.sh_vendor_filter_due_date:
                            worksheet.write(
                                k, 3, str(j.sh_vendor_filter_due_date), red_text
                            )
                        else:
                            worksheet.write(k, 3, "", red_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_filter_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_filter_paid_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_filter_balance)),
                            red_text,
                        )

                    k = k + 1
                total_amount = total_amount + j.sh_vendor_filter_amount
                total_paid_amount = total_paid_amount + j.sh_vendor_filter_paid_amount
                total_balance = total_balance + j.sh_vendor_filter_balance
        if self.sh_filter_vendor_statement_ids:
            worksheet.write(k, 4, str("{:.2f}".format(total_amount)), totals)
            worksheet.row(k).height = 350
            worksheet.write(k, 5, str("{:.2f}".format(total_paid_amount)), totals)
            worksheet.write(k, 6, str("{:.2f}".format(total_balance)), totals)

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env["ir.attachment"]
        attachment_vals = {
            "name": "Vendor Statement Filter By Date.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search(
            [
                ("name", "=", "Vendor Statement Filter By Date"),
                ("type", "=", "binary"),
                ("res_model", "=", "ir.ui.view"),
            ],
            limit=1,
        )
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)
        # TODO: make user error here
        if not attachment:
            raise UserError("There is no attachments...")

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "current",
        }

    def action_print_vendor_statement_xls(self):
        workbook = xlwt.Workbook()

        heading_format = xlwt.easyxf(
            "font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        normal = xlwt.easyxf("font:bold True;align: horiz center;align: vert center")
        cyan_text = xlwt.easyxf(
            "font:bold True,color aqua;align: horiz center;align: vert center"
        )
        green_text = xlwt.easyxf(
            "font:bold True,color green;align: horiz center;align: vert center"
        )
        red_text = xlwt.easyxf(
            "font:bold True,color red;align: horiz center;align: vert center"
        )
        bold_center = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        totals = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        worksheet = workbook.add_sheet("Vendor Statement", cell_overwrite_ok=True)

        worksheet.row(5).height = 400
        worksheet.row(12).height = 400
        worksheet.row(13).height = 400
        worksheet.row(10).height = 350
        worksheet.row(11).height = 350
        worksheet.col(2).width = 4800
        worksheet.col(3).width = 4800
        worksheet.col(4).width = 5500
        worksheet.col(5).width = 5500
        worksheet.col(6).width = 5500
        worksheet.col(0).width = 5500
        worksheet.col(1).width = 6000
        worksheet.write_merge(2, 3, 0, 6, self.name, heading_format)
        worksheet.write(5, 0, "Number", bold_center)
        worksheet.write(5, 1, "Account", bold_center)
        worksheet.write(5, 2, "Date", bold_center)
        worksheet.write(5, 3, "Due Date", bold_center)
        worksheet.write(5, 4, "Total Amount", bold_center)
        worksheet.write(5, 5, "Paid Amount", bold_center)
        worksheet.write(5, 6, "Balance", bold_center)

        total_amount = 0
        total_paid_amount = 0
        total_balance = 0
        k = 6

        if self.sh_vendor_statement_ids:
            for i in self.sh_vendor_statement_ids:
                for j in i:
                    worksheet.row(k).height = 350
                    if j.sh_vendor_amount == j.sh_vendor_balance:
                        worksheet.write(k, 0, j.name, cyan_text)
                        worksheet.write(k, 1, j.sh_account, cyan_text)
                        worksheet.write(k, 2, str(j.sh_vendor_invoice_date), cyan_text)
                        if j.sh_vendor_due_date:
                            worksheet.write(k, 3, str(j.sh_vendor_due_date), cyan_text)
                        else:
                            worksheet.write(k, 3, "", cyan_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_amount)),
                            cyan_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_paid_amount)),
                            cyan_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_balance)),
                            cyan_text,
                        )
                    elif j.sh_vendor_balance == 0:
                        worksheet.write(k, 0, j.name, green_text)
                        worksheet.write(k, 1, j.sh_account, green_text)
                        worksheet.write(k, 2, str(j.sh_vendor_invoice_date), green_text)
                        if j.sh_vendor_due_date:
                            worksheet.write(k, 3, str(j.sh_vendor_due_date), green_text)
                        else:
                            worksheet.write(k, 3, "", green_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_amount)),
                            green_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_paid_amount)),
                            green_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_balance)),
                            green_text,
                        )
                    else:
                        worksheet.write(k, 0, j.name, red_text)
                        worksheet.write(k, 1, j.sh_account, red_text)
                        worksheet.write(k, 2, str(j.sh_vendor_invoice_date), red_text)
                        if j.sh_vendor_due_date:
                            worksheet.write(k, 3, str(j.sh_vendor_due_date), red_text)
                        else:
                            worksheet.write(k, 3, "", red_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_paid_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_vendor_balance)),
                            red_text,
                        )
                    k = k + 1
                total_amount = total_amount + j.sh_vendor_amount
                total_paid_amount = total_paid_amount + j.sh_vendor_paid_amount
                total_balance = total_balance + j.sh_vendor_balance

        if self.sh_vendor_statement_ids:
            worksheet.write(k, 4, str("{:.2f}".format(total_amount)), totals)
            worksheet.row(k).height = 350
            worksheet.write(k, 5, str("{:.2f}".format(total_paid_amount)), totals)
            worksheet.write(k, 6, str("{:.2f}".format(total_balance)), totals)
        worksheet.write(k + 3, 0, "Gap Between Days", bold_center)
        worksheet.write(k + 3, 1, "0-30(Days)", bold_center)
        worksheet.write(k + 3, 2, "30-60(Days)", bold_center)
        worksheet.write(k + 3, 3, "60-90(Days)", bold_center)
        worksheet.write(k + 3, 4, "90+(Days)", bold_center)
        worksheet.write(k + 3, 5, "Total", bold_center)
        worksheet.write(k + 4, 0, "Balance Amount", bold_center)
        if self.sh_vendor_statement_ids:
            worksheet.write(
                k + 4, 1, str("{:.2f}".format(self.sh_vendor_zero_to_thiry)), normal
            )
            worksheet.write(
                k + 4, 2, str("{:.2f}".format(self.sh_vendor_thirty_to_sixty)), normal
            )
            worksheet.write(
                k + 4, 3, str("{:.2f}".format(self.sh_vendor_sixty_to_ninety)), normal
            )
            worksheet.write(
                k + 4, 4, str("{:.2f}".format(self.sh_vendor_ninety_plus)), normal
            )
            worksheet.write(
                k + 4, 5, str("{:.2f}".format(self.sh_vendor_total)), normal
            )

        fp = io.BytesIO()
        workbook.save(fp)
        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env["ir.attachment"]
        attachment_vals = {
            "name": "Vendor Statement.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search(
            [
                ("name", "=", "Vendor Statement"),
                ("type", "=", "binary"),
                ("res_model", "=", "ir.ui.view"),
            ],
            limit=1,
        )
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)
        # TODO: make user error here
        if not attachment:
            raise UserError("There is no attachments...")

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "current",
        }

    def action_print_vendor_due_statement_xls(self):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            "font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        red_text = xlwt.easyxf(
            "font:bold True,color red;align: horiz center;align: vert center"
        )
        center_text = xlwt.easyxf("align: horiz center;align: vert center")
        bold_center = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;align: vert center;borders: left thin, right thin, bottom thin,top thin,top_color gray40,bottom_color gray40,left_color gray40,right_color gray40"
        )
        date = xlwt.easyxf(
            "font:height 225,bold True;pattern: pattern solid,fore_colour gray25;align: horiz center;borders: left thin, right thin, bottom thin;align: vert center;align: horiz left"
        )
        worksheet = workbook.add_sheet(
            "Vendor Overdue Statement", cell_overwrite_ok=True
        )

        now = datetime.now()
        today_date = now.strftime("%d/%m/%Y %H:%M:%S")

        worksheet.write(1, 0, str(str("Date") + str(": ") + str(today_date)), date)
        worksheet.row(1).height = 350
        worksheet.row(6).height = 350
        worksheet.col(0).width = 8000
        worksheet.col(1).width = 6000
        worksheet.col(2).width = 4800
        worksheet.col(3).width = 4800
        worksheet.col(4).width = 5500
        worksheet.col(5).width = 5500
        worksheet.col(6).width = 5500
        worksheet.row(11).height = 350

        worksheet.write_merge(3, 4, 0, 6, self.name, heading_format)
        worksheet.write(6, 0, "Number", bold_center)
        worksheet.write(6, 1, "Account", bold_center)
        worksheet.write(6, 2, "Date", bold_center)
        worksheet.write(6, 3, "Due Date", bold_center)
        worksheet.write(6, 4, "Total Amount", bold_center)
        worksheet.write(6, 5, "Paid Amount", bold_center)
        worksheet.write(6, 6, "Balance", bold_center)

        total_amount = 0
        total_paid_amount = 0
        total_balance = 0
        k = 7

        if self.sh_vendor_due_statement_ids:
            for i in self.sh_vendor_due_statement_ids:
                worksheet.row(k).height = 350
                for j in i:
                    if (
                        j.sh_due_vendor_invoice_date
                        and j.sh_today
                        and j.sh_due_vendor_invoice_date < j.sh_today
                    ):
                        worksheet.write(k, 0, j.name, red_text)
                        worksheet.write(k, 1, j.sh_account, red_text)
                        worksheet.write(
                            k, 2, str(j.sh_due_vendor_invoice_date), red_text
                        )
                        if j.sh_due_vendor_due_date:
                            worksheet.write(
                                k, 3, str(j.sh_due_vendor_due_date), red_text
                            )
                        else:
                            worksheet.write(k, 3, "", red_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_vendor_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_vendor_paid_amount)),
                            red_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_vendor_balance)),
                            red_text,
                        )
                    else:
                        worksheet.write(k, 0, j.name, center_text)
                        worksheet.write(k, 1, j.sh_account, center_text)
                        worksheet.write(
                            k, 2, str(j.sh_due_vendor_invoice_date), center_text
                        )
                        if j.sh_due_vendor_due_date:
                            worksheet.write(
                                k, 3, str(j.sh_due_vendor_due_date), center_text
                            )
                        else:
                            worksheet.write(k, 3, "", center_text)
                        worksheet.write(
                            k,
                            4,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_vendor_amount)),
                            center_text,
                        )
                        worksheet.write(
                            k,
                            5,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_vendor_paid_amount)),
                            center_text,
                        )
                        worksheet.write(
                            k,
                            6,
                            str(i.currency_id.symbol)
                            + str("{:.2f}".format(j.sh_due_vendor_balance)),
                            center_text,
                        )
                    k = k + 1
                total_amount = total_amount + j.sh_due_vendor_amount
                total_paid_amount = total_paid_amount + j.sh_due_vendor_paid_amount
                total_balance = total_balance + j.sh_due_vendor_balance
        if self.sh_vendor_due_statement_ids:
            worksheet.write(k, 4, str("{:.2f}".format(total_amount)), bold_center)
            worksheet.row(k).height = 350
            worksheet.write(k, 5, str("{:.2f}".format(total_paid_amount)), bold_center)
            worksheet.write(k, 6, str("{:.2f}".format(total_balance)), bold_center)

        fp = io.BytesIO()
        workbook.save(fp)

        data = base64.encodebytes(fp.getvalue())
        IrAttachment = self.env["ir.attachment"]
        attachment_vals = {
            "name": "Vendor Overdue Statement.xls",
            "res_model": "ir.ui.view",
            "type": "binary",
            "datas": data,
            "public": True,
        }
        fp.close()

        attachment = IrAttachment.search(
            [
                ("name", "=", "Vendor Overdue Statement"),
                ("type", "=", "binary"),
                ("res_model", "=", "ir.ui.view"),
            ],
            limit=1,
        )
        if attachment:
            attachment.write(attachment_vals)
        else:
            attachment = IrAttachment.create(attachment_vals)
        # TODO: make user error here
        if not attachment:
            raise UserError("There is no attachments...")

        url = "/web/content/" + str(attachment.id) + "?download=true"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "current",
        }


class FilterCustomerStateMent(models.Model):
    _name = "sh.res.partner.filter.statement"
    _description = "Filter Customer Statement"

    partner_id = fields.Many2one("res.partner", "Partner")
    name = fields.Char("Invoice Number")
    currency_id = fields.Many2one("res.currency", "Currency")
    sh_account = fields.Char("Account")
    sh_filter_invoice_date = fields.Date("Invoice Date")
    sh_filter_due_date = fields.Date("Invoice Due Date")
    sh_filter_amount = fields.Monetary("Total Amount")
    sh_filter_paid_amount = fields.Monetary("Paid Amount")
    sh_filter_balance = fields.Monetary("Balance")


class FilterVendorStateMent(models.Model):
    _name = "sh.vendor.filter.statement"
    _description = "Filter Vendor Statement"

    partner_id = fields.Many2one("res.partner", "Partner")
    name = fields.Char("Bill Number")
    currency_id = fields.Many2one("res.currency", "Currency")
    sh_account = fields.Char("Account")
    sh_vendor_filter_invoice_date = fields.Date("Bill Date")
    sh_vendor_filter_due_date = fields.Date("Bill Due Date")
    sh_vendor_filter_amount = fields.Monetary("Total Amount")
    sh_vendor_filter_paid_amount = fields.Monetary("Paid Amount")
    sh_vendor_filter_balance = fields.Monetary("Balance")


class CustomerStateMent(models.Model):
    _name = "sh.customer.statement"
    _description = "Customer Statement"

    partner_id = fields.Many2one("res.partner", "Partner")
    currency_id = fields.Many2one("res.currency", "Currency")
    name = fields.Char("Invoice Number")
    sh_account = fields.Char("Account")
    sh_customer_invoice_date = fields.Date("Invoice Date")
    sh_customer_due_date = fields.Date("Invoice Due Date")
    sh_customer_amount = fields.Monetary("Total Amount")
    sh_customer_paid_amount = fields.Monetary("Paid Amount")
    sh_customer_balance = fields.Monetary("Balance")


class VendorStateMent(models.Model):
    _name = "sh.vendor.statement"
    _description = "Vendor Statement"

    partner_id = fields.Many2one("res.partner", "Partner")
    name = fields.Char("Bill Number")
    currency_id = fields.Many2one("res.currency", "Currency")
    sh_account = fields.Char("Account")
    sh_vendor_invoice_date = fields.Date("Bill Date")
    sh_vendor_due_date = fields.Date("Bill Due Date")
    sh_vendor_amount = fields.Monetary("Total Amount")
    sh_vendor_paid_amount = fields.Monetary("Paid Amount")
    sh_vendor_balance = fields.Monetary("Balance")


class CustomerDueStateMent(models.Model):
    _name = "sh.customer.due.statement"
    _description = "Customer Due Statement"

    partner_id = fields.Many2one("res.partner", "Partner")
    name = fields.Char("Invoice Number")
    currency_id = fields.Many2one("res.currency", "Currency")
    sh_account = fields.Char("Account")
    sh_today = fields.Date("Today")
    sh_due_customer_invoice_date = fields.Date("Invoice Date")
    sh_due_customer_due_date = fields.Date("Invoice Due Date")
    sh_due_customer_amount = fields.Monetary("Total Amount")
    sh_due_customer_paid_amount = fields.Monetary("Paid Amount")
    sh_due_customer_balance = fields.Monetary("Balance")


class VendorDueStateMent(models.Model):
    _name = "sh.vendor.due.statement"
    _description = "Vendor Due Statement"

    partner_id = fields.Many2one("res.partner", "Partner")
    name = fields.Char("Bill Number")
    currency_id = fields.Many2one("res.currency", "Currency")
    sh_account = fields.Char("Account")
    sh_due_vendor_invoice_date = fields.Date("Bill Date")
    sh_today = fields.Date("Today")
    sh_due_vendor_due_date = fields.Date("Bill Due Date")
    sh_due_vendor_amount = fields.Monetary("Total Amount")
    sh_due_vendor_paid_amount = fields.Monetary("Paid Amount")
    sh_due_vendor_balance = fields.Monetary("Balance")
