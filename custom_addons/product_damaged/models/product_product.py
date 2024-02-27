from odoo import models, exceptions, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    def compute_product_as_damaged(self):
        attribute_values = self.env['product.template.attribute.value'].search([('product_tmpl_id', '=',
                                                                                 self.product_tmpl_id.id)])
        damaged_attrs_map = {val.name: val.id for val in attribute_values if val.attribute_id.name == "Quality"}

        if damaged_attrs_map == {} or set(damaged_attrs_map.keys()) != {'OK', 'Damaged'}:
            raise exceptions.UserError(
                _(f"'Quality'-attribute on product {self.product_tmpl_id.name} not found. \nGo to product template 'Attributes & Variants' and add attribute 'Quality'. Add then 'OK' and 'Damaged' as possible values."
                  ))

        attributes = list(map(int, self.combination_indices.split(',')))
        # Replace the value of 'OK' with 'Damaged' in the set of attributes
        replace = lambda lst, x, y: [y if ii == x else ii for ii in lst]
        attributes_damaged = set(replace(attributes, damaged_attrs_map['OK'], damaged_attrs_map['Damaged']))

        if set(attributes) == attributes_damaged:
            raise exceptions.UserError(_(f'Product {self.name} is already marked as damaged'))

        for product in self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)]):
            if set(map(int, product.combination_indices.split(','))) == attributes_damaged:
                return product

        raise exceptions.UserError(_(f'Damaged Product not found for {self.name}'))
