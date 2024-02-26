from odoo import fields, models


class CustomPartner(models.Model):
    _inherit = 'res.partner'

    delivery_score = fields.Float(string='Delivery Score [%]', compute="_compute_delivery_score", help='Delivery Score')
    is_logistic = fields.Boolean(string='Is Logistic Partner', compute='_compute_is_logistic', store=True)

    def _compute_is_logistic(self):
        for record in self:
            record.is_logistic = 'Logistic' in record.category_id.mapped('name')

    def _compute_delivery_score(self):
        for record in self:
            truck_routes = self.env['truck.route'].search([('partner_id', '=', record.id)])
            delivery_performances = []
            for truck_route in truck_routes:
                if truck_route.delivery_time and truck_route.promised_time and truck_route.delivery_time > 0 and truck_route.promised_time > 0:
                    delivery_performances.append((min(truck_route.promised_time / truck_route.delivery_time), 1) * 100)
            if delivery_performances:
                record.delivery_score = sum(delivery_performances) / len(delivery_performances)
            else:
                record.delivery_score = 100.0

    def send_action_email_bid_suppliers(self, pricelist_id=None):
        return {
            'name': 'Pricelist Wizard',
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_id': self.env.ref('fish_market.view_pricelist_wizard_form').id,
            'view_mode': 'form',
            'res_model': 'supplier.price.wizard',
            'target': 'new',
            'context': {
                'default_logistic_partner_ids': self.ids,
                'default_pricelist_id': self.env['product.pricelist'].search([], limit=1).id
            }
        }

    def action_view_trucks(self):
        return {
            'name': 'Trucks',
            'type': 'ir.actions.act_window',
            'res_model': 'truck.route',
            'view_mode': 'tree,form',
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [('partner_id', '=', self.id)],
            'target': 'current',
        }