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
from odoo import fields, models, api


class stock_picking(models.Model):
    _inherit = "stock.picking"

    magento_order = fields.Char(string='Magento Order', size=128)
    magento_picking = fields.Char(string='Magento Pakbon', size=128)

    @api.multi
    def _create_invoice_from_picking(self, picking, vals):
        if vals is None:
            vals = {}

        vals['magento_order'] = (picking and picking.magento_order) or False

        return super(stock_picking, self)._create_invoice_from_picking(picking, vals)

stock_picking()
