
{
    'name': 'Budget-Sanitair Dropship Reports ',
    'version': '1.0',
    'description': """
    Sanitairkamer - reports changes for Budget-Sanitair Dropship Delivery

==================
        """,
    'website': 'www.erpopen.nl',
    'category': '',
    'author': 'Marinka Papeleu Dória, ERP|OPEN',
    'depends': [
        'sanitairkamer_reports',
        'b2b_magento_supplier'
    ],
    'data': [
        'views/bs_dropship_custom_footer.xml',
        'views/bs_dropship_custom_header.xml',
        'views/bs_dropship_picking.xml',
        'views/bs_dropship_report_definitions.xml',
    ],
    #'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
}
