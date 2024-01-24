{
    'name': "Fish_Market",
    'version': '1.0',
    'depends': ['base', 'purchase', 'web', 'fleet', 'stock', 'sale_management',
                'base_accounting_kit', 'hy_currency_rate',
                'cash_exchange', 'pos_absolute_discount', 'pos_multi_currency_cash'],
    'author': "Ludwig Gräf",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',

        'data/email_template.xml',
        'data/email_template_suppliers.xml',
        'data/email_template_logistics.xml',
        'data/logisitc_form_template.xml',
        'data/supplier_form_template.xml',

        'views/damage_views.xml',
        'views/truck_redistribution_wizard.xml',
        'views/truck_seal_wizard.xml',
        'views/pricelist_wizard.xml',
        'views/transport_order.xml',
        'views/res_partner_logisitic_views.xml',
        'views/product.xml',
        'views/stock_picking.xml',

        'views/report_invoice.xml',

        'views/res_partner_bank_views.xml',
        'views/inventory.xml',
        'views/route_wizard.xml',
        'views/pricelist.xml',
        'views/res_partner_supplier_views.xml',
        'report/purchase_report_views.xml',

        'views/truck_view.xml',
        'views/sale_meta_view.xml',
        'views/sale_order_view.xml',
        'views/account_move_view.xml',

        'views/menus.xml',
    ],

    'installable': True,
    'application': True,

    'assets': {
        'web.assets_backend': [
            'fish_market/static/src/views/**/*',
            'fish_market/static/src/scss/*.scss',
        ],
        'web.assets_frontend': [
            'fish_market/static/src/js/*',
            'fish_market/static/src/scss/*',
        ],
    },
    'license': 'LGPL-3',
}