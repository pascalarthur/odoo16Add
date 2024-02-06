{
    'name': "Fish_Market",
    'version': '1.0',
    'depends': ['base', 'purchase', 'web', 'fleet', 'stock', 'sale_management',
                'dynamic_accounts_report', 'hy_currency_rate',
                'pos_absolute_discount', 'pos_multi_currency_cash',
                'pos_receipt_extend', 'pos_closing_transaction', 'pos_invoice_automate',
                'bi_inter_company_transfer', 'cash_exchange'],
    'author': "Ludwig Gräf",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
    ],

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}