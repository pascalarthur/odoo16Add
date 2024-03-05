# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models


class ExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def _sh_remove_moves(self):
        self.ensure_one()
        if self.account_move_ids:
            account_partial_reconcile_ids = self.account_move_ids.mapped(
                lambda x: (x.line_ids.matched_debit_ids + x.line_ids.matched_debit_ids))
            reconciled_moves = account_partial_reconcile_ids.credit_move_id.move_id + \
                account_partial_reconcile_ids.debit_move_id.move_id
            account_partial_reconcile_ids.unlink()
            moves_to_unlink = reconciled_moves or self.account_move_ids
            moves_to_unlink.button_draft()
            moves_to_unlink.unlink()

    def action_expense_cancel(self):
        for rec in self:
            rec_su = rec.sudo()
            rec_su.expense_line_ids.write({'state': 'refused'})
            rec_su._sh_remove_moves()
            rec_su.write({'state': 'cancel'})

    def action_expense_cancel_draft(self):
        for rec in self:
            rec_su = rec.sudo()
            rec_su.expense_line_ids.write({'state': 'draft'})
            rec_su._sh_remove_moves()
            rec_su.write({'state': 'draft'})

    def action_expense_cancel_delete(self):
        for rec in self:
            rec_su = rec.sudo()
            rec_su.expense_line_ids.write({'state': 'refused'})
            rec_su.expense_line_ids.unlink()
            rec_su._sh_remove_moves()
            rec_su.write({'state': 'cancel'})
            rec_su.unlink()

    def sh_cancel(self):

        if self.sudo().mapped('expense_line_ids'):
            if self.company_id.expense_operation_type == 'cancel':
                self.action_expense_cancel()
            elif self.company_id.expense_operation_type == 'cancel_draft':
                self.action_expense_cancel_draft()
            elif self.company_id.expense_operation_type == 'cancel_delete':
                self.action_expense_cancel_delete()
                return {
                    'name': 'Expense Report',
                    'type': 'ir.actions.act_window',
                    'res_model': 'hr.expense.sheet',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'target': 'current',
                }
