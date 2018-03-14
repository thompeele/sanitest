
{
    'name': 'Sanitairkamer Reports ',
    'version': '1.0',
    'description': """
    Sanitairkamer - reports changes
        Before installing this module, make sure the following settings are set:
        1. Sales/Settings > show 3 address fields on sales order: client, invoice and shipping
        2. Sales/Settings > Allow to modify the sales order dates to postpone deliveries and procurements
==================
        """,
    'website': 'www.erpopen.nl',
    'category': '',
    'author': 'Marinka Papeleu Dória, ERP|OPEN',
    'depends': [
        'account',
        'sale',
        'stock',
        'purchase',
        'business_2_business',
        'erpopen_magento_odoo',
    ],
    'data': [
        'views/sk_custom_header.xml',
        'views/sk_custom_footer.xml',
        'views/sk_custom_invoice.xml',
        'views/sk_custom_picking.xml',
        'views/sk_custom_saleorder.xml',
        'views/sk_custom_purchaseorder.xml',
        'views/sk_invoice_report_definitions.xml',
    ],
    #'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
}
