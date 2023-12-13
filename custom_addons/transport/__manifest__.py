{
    'name': "Transport",
    'version': '1.0',
    'depends': ['base', 'purchase', 'web', 'fleet', 'stock', 'sale_management'],
    'author': "Author Name",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',

        'views/route.xml',
        'views/res_partner_logisitic_views.xml',

        'views/menus.xml',
    ],

    'installable': True,
    'application': True,

    'assets': {
        'web.assets_backend': [
            # 'transport/static/src/views/**/*',
            # 'transport/static/src/scss/*.scss',
        ],
    },
    'license': 'LGPL-3',
}