# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

{
    "name": "Cancel Purchase Orders",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Purchases",
    "license": "OPL-1",
    "summary": "Cancel Purchases Orders Cancel PO Purchase Order Cancel RFQs Cancel Request For Quotation Purchase Cancel Delete Purchase Order Delete PO Delete RFQ Remove Purchase Order Cancellation of purchase order Odoo",
    "description": """
This module helps to cancel created purchase orders. You can also cancel multiple purchase orders from the tree view. You can cancel the purchase order in 3 ways,

1) Cancel Only: When you cancel a purchase order then the purchase order is cancelled and the state is changed to "cancelled".
2) Cancel and Reset to Draft: When you cancel purchase order, first purchase order is cancelled and then reset to the draft state.
3) Cancel and Delete: When you cancel a purchase order then first purchase order is cancelled and then purchase order will be deleted.

We provide 2 options in the cancel purchase orders,

1) Cancel Receipt: When you want to cancel purchase orders and receipt then you can choose this option.
2) Cancel Bill and Payment: When you want to cancel purchase orders and bill then you can choose this option.

If you want to cancel purchase orders, receipts & bill then you can choose both options "Cancel Receipt" & "Cancel Bill and Payment".""",
    "version": "0.0.1",
    "depends": [
                "purchase",

    ],
    "application": True,
    "data": [
        'security/purchase_security.xml',
        'data/server_action_data.xml',
        'views/purchase_config_settings_views.xml',
        'views/purchase_order_views.xml',
    ],
    "images": ["static/description/background.png", ],
    "auto_install": False,
    "installable": True,
    "price": 20,
    "currency": "EUR"
}
