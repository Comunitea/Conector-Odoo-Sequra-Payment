# -*- coding: utf-8 -*-

{
    'name': 'SeQura Payment Acquirer',
    'summary': 'SeQura Acquirer: SeQura Implementation',
    'version': '11.0.1',
    'description': """SeQura Payment Acquirer""",
    'author': 'Raul Fidel Rodríguez Trasanco',
    'depends': ['product', 'delivery', 'payment', 'website', 'website_sale','account_payment'],
    'data': [
            'views/sequra.xml',
            'data/sequra.xml',
            'views/payment_acquirer.xml',
            'views/res_config_view.xml',
            'views/website_template.xml',
            'views/sale_view.xml',
             'views/product.xml'
    ],
    'installable': True,
}
