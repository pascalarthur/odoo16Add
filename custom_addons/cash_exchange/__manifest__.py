{
    'name': "Cash Exchange",
    'version': '1.0',
    'depends': ['base', 'account'],
    'author': "Ludwig Gräf",
    'category': 'Category',
    'description': """""",

    'data': [
        'security/ir.model.access.csv',

        'views/account_journal_views.xml',
        'views/account_journal_currency_exchange.xml',
        'views/cash_dasboard.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
}