{
    "name":
    "Intercompany Transfer",
    "version":
    "17.0.0.0",
    "category":
    "Warehouse",
    "description":
    """
            intercompany,
            odoo intercompany,
            odoo intercompany for community,
            intercompany transfer,
            intercompany transaction,
            stock intercompany transaction,
            stock intercompany transfer,
            reverse intercompany transfer,
            reverse intercompany transaction,
    """,
    "author":
    "Ludwig Gräf",
    "price":
    79,
    "currency":
    'EUR',
    "depends": ['base', 'sale_management', 'purchase', 'stock', 'account', 'sale_stock'],
    "data": [
        'security/int_security.xml',
        'security/ir.model.access.csv',
        'data/intercompany_transfer_sequence.xml',
        'views/intercompany_transfer_views.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    "auto_install":
    False,
    "installable":
    True,
    'license':
    'OPL-1',
    "images": ["static/description/Banner.gif"],
}
