# -*- coding: utf-8 -*-

# Copyright © 2018 Garazd Creation (<https://garazd.biz>)
# @author: Yurii Razumovskyi (<support@garazd.biz>)
# @author: Iryna Razumovska (<support@garazd.biz>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

{
    'name': 'Custom Product Labels',
    'version': '14.0.1.0.0',
    'category': 'Inventory',
    'author': 'Garazd Creation',
    'website': 'https://garazd.biz',
    'license': 'LGPL-3',
    'summary': 'Print custom product labels with barcode',
    'images': ['static/description/banner.png'],
    'live_test_url': 'https://apps.garazd.biz/r/1Jw',
    'description': """
Module allows to print custom product barcode labels and tags on different paper formats.
This module include the one label template with size: 57x35mm, paperformat: A4 (21 pcs per sheet, 3 pcs x 7 rows).
    """,
    'depends': [
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/product_label_templates.xml',
        'report/product_label_reports.xml',
        'wizard/print_product_label_views.xml',
    ],
    'demo': [
        'demo/product_demo.xml',
    ],
    'external_dependencies': {
    },
    'support': 'support@garazd.biz',
    'application': False,
    'installable': True,
    'auto_install': False,
}
