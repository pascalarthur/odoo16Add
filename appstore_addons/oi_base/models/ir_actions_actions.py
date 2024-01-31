'''
Created on May 12, 2019

@author: Zuhair Hammadi
'''
from odoo import models, api, _
from .arabic_number import amount_to_text_ar, en_to_ar
from odoo.tools.safe_eval import json, wrap_module

re = wrap_module(__import__('re'), ['match', 'search', 'split'])

class IrActions(models.Model):
    _inherit = 'ir.actions.actions'
    
    @api.model
    def _get_eval_context(self, action=None):
        res = super(IrActions, self)._get_eval_context(action = action)
                
        res.update({
            'json' : json,
            're' : re,     
            'en_to_ar' : en_to_ar,
            'amount_to_text_ar' : amount_to_text_ar,
            '_t' : _             
            })
        
        if 'log' not in res:
            def log(message, path="", line="", func="",  level="info"):
                with self.pool.cursor() as cr:
                    cr.execute("""
                        INSERT INTO ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func)
                        VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (self.env.uid, 'server', self._cr.dbname, __name__, level, message, path, line, func))
            res['log'] = log
            
        
        return res