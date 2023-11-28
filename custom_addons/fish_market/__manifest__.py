{
    'name': "Fish_Market",
    'version': '1.0',
    'depends': ['base', 'purchase'],
    'author': "Author Name",
    'category': 'Category',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'views/index.xml',
        'views/menus.xml',
        'views/custom_purchase_view.xml',

        'report/purchase_report_views.xml',
    ],
    # data files containing optionally loaded demonstration data
    # 'demo': [
    #     'data/purchase_demo.xml',
    # ],
    'license': 'LGPL-3',
}