{
    'name': 'Point of Sale (POS) - Customer Search',
    'depends': ['point_of_sale'],
    'author': "Ludwig Gräf",
    'description': "Allows you to select customer from Product Screen.",
    'price': 30,
    'currency': 'EUR',
    'category': 'Point of Sale',
    'version': '17.0.0.0.0',
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_client_search/static/src/js/pos.js',
            'pos_client_search/static/src/xml/**/*',
        ],
    },
    'images': ['static/description/cover.png'],
    'license': 'OPL-1',
}
