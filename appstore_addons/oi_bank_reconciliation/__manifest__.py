# -*- coding: utf-8 -*-
{
    'name':
    'Bank Statement Reconciliation',
    'summary':
    'Reconciliation, Bank Reconciliation, Invoice Reconciliation, Payment '
    'Reconciliation, Bank Statement',
    'description':
    '''
        * Bank Statement Reconciliation
    ''',
    'author':
    'Openinside',
    'license':
    'OPL-1',
    'website':
    'https://www.open-inside.com',
    'price':
    159.0,
    'currency':
    'USD',
    'category':
    'Accounting',
    'version':
    '17.0.1.2.2',
    'depends': ['account', 'oi_base'],
    'data': [
        'views/account_bank_statement.xml', 'views/account_bank_statement_line.xml', 'views/account_payment.xml',
        'views/account_move_line.xml', 'views/account_journal.xml', 'views/account_bank_statement_generate.xml',
        'views/action.xml', 'views/menu.xml', 'security/ir.model.access.csv'
    ],
    'odoo-apps':
    True,
    'auto_install':
    False,
    'images': ['static/description/cover.png'],
    'application':
    False
}
