{
    'name': "Cash Exchange",
    'version': '1.0',
    'depends': ['base', 'account', 'bi_manual_currency_exchange_rate_invoice_payment'],
    'author': "Ludwig Gräf",
    'category': 'Category',
    'description': """""",

    'data': [
        'security/ir.model.access.csv',

        'views/invoice_view.xml',
        'views/account_account_views.xml',
        'views/account_account_currency_exchange.xml',
        'views/account_payment_view.xml',
        'views/cash_dasboard.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
}