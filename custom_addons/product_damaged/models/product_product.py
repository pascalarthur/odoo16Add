from odoo import models, exceptions, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    def compute_product_as_damaged(self):
        attribute_values = self.env['product.template.attribute.value'].search([('product_tmpl_id', '=',
                                                                                 self.product_tmpl_id.id)])
        attribute_values_map = {}
        for attr_val in attribute_values:
            if attr_val.attribute_id.name == "Quality":
                attribute_values_map[attr_val.name] = attr_val.id

        if attribute_values_map == {}:
            raise exceptions.UserError(
                _(f"'Quality'-attribute on product {self.product_tmpl_id.name} not found.\
                                            Go to product template 'Attributes & Variants' and add attribute 'Quality'")
            )

        attributes = map(int, self.combination_indices.split(','))
        attributes_damaged = set(
            [x if x != attribute_values_map['OK'] else attribute_values_map['Damaged'] for x in attributes])

        for product in self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)]):
            if set(map(int, product.combination_indices.split(','))) == attributes_damaged:
                return product

        raise exceptions.UserError(_(f'Damaged Product not found for {self.name}'))
