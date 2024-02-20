{
    'name': "Point of Sale - Payment Screen Summary",
    'version': '17.0',
    'depends': ['base', 'point_of_sale'],
    'author': "Ludwig Gräf",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_payment_screen_summary/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
