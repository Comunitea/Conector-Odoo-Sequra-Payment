# -*- coding: utf-8 -*-

{
    'name': 'SeQura Payment Acquirer',
    'summary': 'SeQura Acquirer: SeQura Implementation',
    'version': '12.0.0',
    'description': """SeQura Payment Acquirer""",
    'author': 'Raul Fidel Rodríguez Trasanco',
    'contributors': [
        'Comunitea Servicios Tecnológicos S.L. <info@comunitea.com>'
        'Vicente Ángel Gutiérrez <vicente@comunitea.com>',
    ],
    'depends': ['product', 'delivery', 'payment', 'website', 'website_sale','account_payment'],
    'data': [
            'views/assets.xml',
            'views/template.xml',
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
