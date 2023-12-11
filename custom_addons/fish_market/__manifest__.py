{
    'name': "Fish_Market",
    'version': '1.0',
    'depends': ['base', 'purchase', 'web', 'fleet', 'stock', 'sale'],
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
        'views/res_partner_logisitic_views.xml',
        'views/custom_purchase_view.xml',
        'report/purchase_report_views.xml',
        'views/sale_order_view.xml',

        'views/menus.xml',
    ],

    'installable': True,
    'application': True,

    'assets': {
        # 'web.assets_backend': [
        #     # 'fish_market/static/src/js/sale_kanban_button.js',
        #     # 'fish_market/static/src/xml/sale_kanban_button.xml',
        #     'fish_market/static/src/scss/style.scss',
        #     # 'fish_market/static/src/js/custom_image_widget.js',
        #     # 'fish_market/static/src/css/style.css',
        #     # 'fish_market/static/src/css/progress_bar_widget.css',
        #     # 'fish_market/static/src/js/progress_bar_widget.js',
        # ],
        'web.assets_backend': [
            'fish_market/static/src/views/**/*',
            'fish_market/static/src/scss/*.scss',
        ],
    },
    'license': 'LGPL-3',
}