{
    'name': "Compute Profit on Unit Level",
    'version': '17.0.0.0.0',
    'depends': ['base', 'account', 'product', 'sale_management', 'purchase', 'stock', 'account', 'sale_stock'],
    'author': "Ludwig Gräf",
    'price': 35.0,
    'currency': 'USD',
    'category': 'Warehouse',
    'description': """
    Convert Damaged Products
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'wizards/unit_level_profit_wizard.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
    'images': ['static/description/cover.png'],
}
