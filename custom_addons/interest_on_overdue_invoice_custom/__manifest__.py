{
    'name': "Interest on overdue Invoice",
    'version': '17.0.0.0.0',
    'depends': ['base', 'account'],
    'author': "Ludwig Gräf",
    'price': 15.0,
    'currency': 'USD',
    'category': 'Warehouse',
    'description': """
    Interest on overdue Invoice
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'views/account_payment_term_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
