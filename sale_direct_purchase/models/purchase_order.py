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

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=None):
        _logger.debug("Context PO: %s", self._context)
        if self._context.get('direct_fulfill'):
            origin_arg = ('origin', '=', self._context.get('direct_fulfill'))
            args.append(origin_arg)
            return super(PurchaseOrder, self).search(
                    args,
                    offset=offset,
                    limit=limit,
                    order=order,
                    count=count
            )
        else:
            return super(PurchaseOrder, self).search(
                    args, offset=offset, limit=limit, order=order, count=count)