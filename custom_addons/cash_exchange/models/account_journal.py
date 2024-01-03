from odoo import _, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    location_id = fields.Many2one('stock.location', 'Location')

    def action_open_payment_form(self):
        # Logic to open the standard payment form
        # Pre-fill necessary fields based on the journal selected
        return {
            'name': 'Register Payment',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.journal.currency.exchange',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_journal_id': self.id,
                'default_location_id': self.location_id.id,
                # Add other default fields if necessary
            }
        }
