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

        'views/pos_session_view.xml',
    ],

    'installable': True,

    'assets': {
        'web.assets_backend': [
            'pos_multi_currency/static/src/views/**/*',
            'pos_multi_currency/static/src/scss/*.scss',
        ],
    },
    'license': 'LGPL-3',
}