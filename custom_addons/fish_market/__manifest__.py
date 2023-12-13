{
    'name': "Fish_Market",
    'version': '1.0',
    'depends': ['base', 'purchase', 'web', 'fleet', 'stock', 'sale_management', 'transport'],
    'author': "Author Name",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',

        'data/email_template_suppliers.xml',
        'data/email_template_logistics.xml',

        'views/inventory.xml',
        'views/route.xml',
        'views/quotation_management_view.xml',
        'views/index.xml',
        'views/res_partner_supplier_views.xml',
        'views/custom_purchase_view.xml',
        'report/purchase_report_views.xml',
        'views/sale_order_view.xml',

        'views/menus.xml',
    ],

    'installable': True,
    'application': True,

    'assets': {
        'web.assets_backend': [
            'fish_market/static/src/views/**/*',
            'fish_market/static/src/scss/*.scss',
        ],
    },
    'license': 'LGPL-3',
}