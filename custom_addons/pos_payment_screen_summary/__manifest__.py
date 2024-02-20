{
    'name': "Point of Sale - Payment Screen Summary",
    'depends': ['base', 'point_of_sale'],
    'author': "Ludwig Gräf",
    'description': """
    Module that displays a summary of the orders on the payment screen.
    """,
    'price': 5.0,
    'currency': 'USD',
    'category': 'Accounting',
    'version':'17.0.0.0.0',

    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_payment_screen_summary/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
