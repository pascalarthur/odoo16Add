{
    'name': "Point of Sale - Multiple Currencies",
    'version': '1.0',
    'depends': ['base', 'point_of_sale'],
    'author': "Ludwig Gräf",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_multi_currency/static/src/js/pos_data.js',
            'pos_multi_currency/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
