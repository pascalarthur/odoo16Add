{
    'name': "Fish_Market",
    'version': '1.0',
    'depends': ['base', 'purchase', 'web', 'fleet'],
    'author': "Author Name",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'views/index.xml',
        'views/res_partner_supplier_views.xml',
        'views/custom_purchase_view.xml',

        'report/purchase_report_views.xml',
        'views/menus.xml',
    ],

    'installable': True,
    'application': True,

    'assets': {
        'web.assets_backend': [
            'fish_market/static/src/**/*',
            # 'fish_market/static/src/js/custom_image_widget.js',
            # 'fish_market/static/src/css/style.css',
            # 'fish_market/static/src/css/progress_bar_widget.css',
            # 'fish_market/static/src/js/progress_bar_widget.js',
        ],
        'web.assets_qweb': [
            # 'fish_market/static/src/xml/progress_bar_widget.xml',
        ],
    },
    'license': 'LGPL-3',
}