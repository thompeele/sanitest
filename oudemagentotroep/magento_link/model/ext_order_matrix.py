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

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class ExtOrderMatrix(models.Model):
    _name = "ext.order.matrix"

    @api.model
    def _get_default_payment_term(self):
        return self.env['account.payment.term'].search([], limit=1)

    ext_delivery = fields.Char(string='Ext Delivery', required=1)
    ext_payment = fields.Char(string='Ext Payment', required=1)
    order_policy = fields.Selection(
        selection=[('manual', 'On Demand'),
                   ('picking', 'On Delivery Order'),
                   ('prepaid', 'Before Delivery'), ],
        string='Desired Order Policy',
        help="What order policy needs to be used.",
        default='manual')
    payment_term = fields.Many2one(
        comodel_name='account.payment.term',
        string='Payment Term', default=_get_default_payment_term)

    @api.multi
    def get_order_values(self):
        res = {}
        for rec in self:
            if rec.payment_term:
                res['payment_term_id'] = rec.payment_term.id
        return res
