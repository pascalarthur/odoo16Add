{
    'name': "Point of Sale - Multiple Currencies - Cash",
    'version': '1.0',
    'depends': ['base', 'point_of_sale', 'pos_multi_currency'],
    'author': "Ludwig Gräf",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'views/pos_config.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [],
    },
    'license': 'LGPL-3',
}
