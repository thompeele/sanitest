# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 More2Make (<http://www.more2make.nl>).
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
    'name': 'Sale order Shipment Info',
    'version': '10.0.0.0.1',
    'category': 'Stock',
    'author': 'More2make',
    'website': 'http://www.more2make.nl',
    'license': 'AGPL-3',
    'summary': 'Adds additional shipment info to sales_order',
    'depends': [
        'sale_stock'
    ],
    'data': [
        'views/sale_order.xml',
    ],
}