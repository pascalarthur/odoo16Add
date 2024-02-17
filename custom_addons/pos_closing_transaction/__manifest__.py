{
    'name': "Point of Sale - Transfer Money",
    'version': '1.0',
    'depends': ['base', 'point_of_sale', 'pos_multi_currency'],
    'author': "Ludwig Gräf",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'views/point_of_sale_dashboard.xml',
        'views/deposit_wizard_views.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_multi_currency_cash/static/src/js/pos_data.js',
            'pos_multi_currency_cash/static/src/xml/**/*',
            'pos_multi_currency_cash/static/src/css/**/*',
        ],
    },
    'license': 'LGPL-3',
}
