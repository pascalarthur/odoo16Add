'''
Created on Nov 15, 2020

@author: Zuhair Hammadi
'''
from odoo import models, fields

class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    statement_line_ids = fields.Many2many(comodel_name='account.bank.statement.line', 
                                          relation='account_payment_account_bank_statement_line_rel',
                                          string = 'Auto-generated for statements') 
    
    match_statement_line_ids = fields.Many2many('account.bank.statement.line', relation='bank_statement_line_matched_payment_rel')
    
    search_statement_matched_payment_id = fields.Many2one("account.bank.statement.line", store = False, search = "_search_statement_matched_payment_id")
    
    
    def _search_statement_matched_payment_id(self, operator, value):
        line_id = self.env["account.bank.statement.line"].browse(value)
        domain = [('journal_id','=', line_id.journal_id.id), ('is_matched','=', False), ('state','=', 'posted'), line_id.amount > 0 and ('payment_type','=', 'inbound') or ('payment_type','=', 'outbound') ]
        ids = self.search(domain).ids
        return [('id','in', ids)]