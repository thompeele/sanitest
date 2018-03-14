# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2015 ERP|OPEN (www.erpopen.nl).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Magento Link',
    'version': '1.0',
    'category': 'Magento',
    'author': 'ERP|OPEN | André Schenkels',
    'website': 'http://www.erpopen.nl',
    'license': 'AGPL-3',
    'summary': 'Base Magento Link module',
    'depends': [
        'account',
        'sale_stock',
        'account_accountant',
        'delivery',
        'website_sale',
        'partner_street_number',
        'base_action_rule',
    ],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        # Views/ Wizards
        'wizard/message_wizard_view.xml',
        'wizard/status_wizard_view.xml',
        'view/magento_configure.xml',
        'view/magento_store.xml',
        'view/magento_sync_history.xml',
        'view/magento_synchronization.xml',
        'view/link_view.xml',
        'view/product_product.xml',
        'view/ext_order_matrix.xml',
        'view/account_invoice.xml',
        'view/sale_order.xml',
        'view/magento_attribute.xml',
        'view/magento_attribute_set.xml',
        'view/magento_attribute_option.xml',
        'view/stock_picking.xml',
        # Menus and Data
        'data/link_menu.xml',
        'data/link_sequence.xml',
        #'data/link_data.xml',
        'data/link_cron.xml',
        'data/link_actions.xml',
    ],
}
