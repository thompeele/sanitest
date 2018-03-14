# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2015 ICTSTUDIO (www.ictstudio.eu).
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

from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        self.ensure_one()
        res = super(StockMove, self)._get_new_picking_values()
        if self.procurement_id and self.procurement_id.sale_line_id and self.procurement_id.sale_line_id.order_id:
            res.update({'client_order_ref': self.procurement_id.sale_line_id.order_id.client_order_ref})
        return res
