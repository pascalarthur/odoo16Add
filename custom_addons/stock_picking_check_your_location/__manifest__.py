{
    'name':
    "Validate Location for Stock Picking",
    'version':
    '17.0.0.0.0',
    'depends': ['base', 'stock'],
    'author':
    "Ludwig Gräf",
    'price':
    15.0,
    'currency':
    'USD',
    'category':
    'Warehouse',
    'description':
    """
    Validate Location for Stock Picking
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/stock_picking_check_location_wizard.xml',
    ],
    'installable':
    True,
    'application':
    True,
    'license':
    'OPL-1',
    'images': ['static/description/cover.png'],
}
