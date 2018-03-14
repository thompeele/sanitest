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

from odoo import models, fields, api, _
from odoo import fields
from odoo import SUPERUSER_ID, tools
import logging
_logger = logging.getLogger(__name__)


class ExtOrderMatrix(models.Model):
    _inherit = "ext.order.matrix"

    auto_invoice = fields.Boolean(
        string='Automatic Invoice on Delivery',
        help="When the order is fully delivered automatic "
             "creation of Invoice should happen.", default=0)

    @api.multi
    def get_order_values(self):
        res = super(ExtOrderMatrix, self).get_order_values()
        for rec in self:
            if rec.auto_invoice:
                res['auto_invoice'] = rec.auto_invoice
        return res
