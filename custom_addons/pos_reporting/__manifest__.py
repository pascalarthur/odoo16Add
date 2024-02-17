{
    'name':
    "Point of Sale - Reporting on Employee Level",
    'version':
    '1.0',
    'depends': ['base', 'point_of_sale'],
    'author':
    "Ludwig Gräf",
    'category':
    'Category',
    'description':
    """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'security/ir.model.access.csv',
        'views/employee_dasboard.xml',
        'views/pos_employee_report.xml',
        'views/menu.xml',
    ],
    'installable':
    True,
    'license':
    'LGPL-3',
}
