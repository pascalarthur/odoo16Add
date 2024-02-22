{
    'name': "Inventory Damaged Products",
    'version': '1.0',
    'depends': ['base', 'product', 'sale_management', 'purchase', 'stock', 'account', 'sale_stock'],
    'author': "Ludwig Gräf",
    'category': 'Inventory/Inventory',
    'description': """
    Convert products to damaged products.
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'data/product_damages_sequence.xml',
        'views/stock_picking.xml',
        'views/damage_views.xml',
        'views/stock_quant.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3'
}
