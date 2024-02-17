{
    'name': "Point of Sale - Absolute Discount",
    'version': '17.0',
    'depends': ['base', 'point_of_sale'],
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
        'point_of_sale._assets_pos': [
            'pos_absolute_discount/static/src/js/pos_data.js',
            # 'pos_absolute_discount/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
