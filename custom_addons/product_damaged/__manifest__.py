{
    'name':
    "Inventory Damaged Products",
    'version':
    '17.0.0.0.0',
    'depends': ['base', 'product', 'sale_management', 'purchase', 'stock', 'account', 'sale_stock'],
    'author':
    "Ludwig Gräf",
    'price':
    35.0,
    'currency':
    'USD',
    'category':
    'Warehouse',
    'description':
    """
    Convert Damaged Products
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'data/product_damages_sequence.xml',
        'views/stock_move_line_views.xml',
        'views/stock_picking.xml',
        'views/stock_quant.xml',
        'views/menu.xml',
    ],
    'installable':
    True,
    'application':
    True,
    'license':
    'OPL-1',
    'images': ['static/description/cover.png'],
}
