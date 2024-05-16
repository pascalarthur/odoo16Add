# -*- coding: utf-8 -*-
{
    'name': 'Discount in Amount on Sale and Invoice | Discount Amount on Sale and Invoice',
    'category': 'Sales',
    'summary': 'This apps helps you to show Discount Amount on Sale Order and Invoice and Reports | Discount in Amount | Discount Amount on Sale Order | Discount Amount on Invoice',
    'description': """
This apps helps you to show Discount Amount on Sale Order and Invoice.
""",
    'author': 'Preway IT Solutions',
    'version': '1.0',
    'depends': ['account', 'sale_management'],
    "data": [
        'views/sale_order_view.xml',
        'views/account_move_view.xml',
        'report/report_sale.xml',
        'report/report_invoice.xml',
    ],
    'price': 10.0,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    "license": "LGPL-3",
    "images":["static/description/Banner.png"],
}
