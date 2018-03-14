# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 ERPOpen (<http://www.erpopen.nl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Business 2 Business Magento Supplier',
    'version': '10.0.0.0.3',
    'category': 'Stock',
    'author': 'ERPOpen | Alaney Dória',
    'website': 'http://www.erponpen.nl',
    'license': 'AGPL-3',
    'summary': 'Customization for Business 2 business and magento',
    'depends': ['business_2_business', 'erpopen_magento_odoo'],
    'data': ['views/sale_order_view.xml'],
}