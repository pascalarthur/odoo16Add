# Copyright 2021 Ivan Yelizariev <https://twitter.com/yelizariev>
# License MIT (https://opensource.org/licenses/MIT).
{
    "name": """Absolute Discounts in POS""",
    "summary": """Set absolute discount if the percentages are not convenient or just boring""",
    "category": "Point of Sale",
    # "live_test_url": 'http://apps.it-projects.info/shop/product/pos-orderline-absolute-discount?version=14.0',
    "images": ["images/pos_orderline_abs_disc_main.png"],
    "version": "14.0.1",
    "application": False,
    "author": "IT-Projects LLC, Dinar Gabbasov",
    "support": "help@itpp.dev",
    "website": "https://github.com/itpp-labs/pos-addons",
    "license": "Other OSI approved licence",  # MIT
    "depends": ["point_of_sale"],
    "external_dependencies": {"python": [], "bin": []},
    "data": [
        "views/pos_order_view.xml",
        "views/pos_config_view.xml",
        "views/report_saledetails.xml",
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_orderline_absolute_discount/static/src/js/models.js',
            'pos_orderline_absolute_discount/static/src/js/screens.js',
            'pos_orderline_absolute_discount/static/src/css/pos_styles.css',
            'pos_orderline_absolute_discount/static/src/js/tour.js'
        ],
    },
    "qweb": ["static/src/xml/pos.xml"],
    "demo": [],
    "post_load": None,
    "pre_init_hook": None,
    "post_init_hook": None,
    "auto_install": False,
    "installable": True,
}
