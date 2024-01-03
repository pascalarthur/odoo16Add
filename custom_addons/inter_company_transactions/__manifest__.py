{
    'name': "Inter Company Transactions",
    'version': '1.0',
    'depends': ['base', 'purchase', 'sale'],
    'author': "Ludwig Gräf",
    'category': 'Category',
    'description': """Description text""",

    'data': [
        'security/ir.model.access.csv',

        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
}