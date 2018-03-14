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

import logging
from odoo import models, fields, api, _


_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    magento_transport = fields.Char(
        related='group_id.magento_transport',
        string='Magento Transport',
        store=True
    )

    @api.model
    def _create_invoice_from_picking(self, picking, vals):
        if vals is None:
            vals = {}

        if picking and picking.magento_transport:
            vals['magento_transport'] = picking.magento_transport

        return super(StockPicking, self)._create_invoice_from_picking(
                picking,
                vals
        )
