# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

{
    "name": "Point Of Sale Session - Cancel & Delete | Cancel Point Of Sale Session | Delete Point Of Sale Session",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "point of sale",
    "license": "OPL-1",
    "summary": "pos cancel from frontend pos order cancel cancel pos order cancel point of sale order pos order cancel from screen Cancel POS Delete POS Order delete Point Of Sale remove pos order remove point of sale cancel pos session cancel pos order session delete pos session cancel and delete pos session delete Cancel Point Of Sale Order Session Delete Point Of Sale Order Session Odoo",
    "description": """This module helps to cancel point of sale sessions. You can cancel the pos sessions in 2 ways,

1) Cancel: When you cancel the session, session is canceled. The POS orders, pickings and journal entries linked with that session also canceled.
2) Cancel and Delete: When you cancel the session then first the session is canceled and then the session will be deleted. The POS orders, pickings and journal entries linked with that session also canceled & deleted.""",
    "version": "0.0.1",
    "depends": [
                "point_of_sale",

    ],
    "application": True,
    "data": [
        'security/sh_pos_session_cancel_groups.xml',
        'views/pos_session_views.xml',
        'views/res_config_settings_views.xml',
    ],
    "auto_install": False,
    "installable": True,
    "images": ["static/description/background.png", ],
    "price": 40,
    "currency": "EUR"

}
