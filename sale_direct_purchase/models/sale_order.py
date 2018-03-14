# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 ICTSTUDIO (<http://www.ictstudio.eu>).
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

from odoo import api, models, _
from odoo.exceptions import Warning as UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_cancel(self):
        """
        Cancel the linked fullfillment PO
        """
        purchase_orders = self.env['purchase.order']
        for so in self:
            so_dom = [('sale_order_id', '=', so.id)]
            procs = self.env['procurement.order'].search(so_dom)
            purchase_orders = procs.mapped('purchase_id')
        res = super(SaleOrder, self).action_cancel()
        for po in purchase_orders:
            if po.state not in ('draft', 'cancel'):
                raise UserError(
                    _("Cannot cancel this sales order!"),
                    _("First cancel the following associated "
                      "Purchase Order : \n%s")
                    % po.name)
            po.action_cancel()
        return res
