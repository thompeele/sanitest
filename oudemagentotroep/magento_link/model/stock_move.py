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

from odoo import models, api
import logging
_logger = logging.getLogger(__name__)


class stock_move(models.Model):
    _inherit = "stock.move"

    @api.multi
    def action_done(self):
        """ Process completly the moves given as ids and if all moves are done, it will finish the picking.
        """
        res = super(stock_move, self).action_done()
        sync_ids = []
        for move in self:
            product = self.env['product.product']
            if move.product_id and not move.product_id.id in sync_ids:
                sync_ids.append(move.product_id.id)
        if sync_ids:
            _logger.debug("Product Sync Yes: %s", sync_ids)
            product.product_sync_yes()
