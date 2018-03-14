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
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    purchase_order_ids = fields.Many2many(
            comodel_name='purchase.order',
            compute='_compute_purchase_order_count',
            string="Purchase Orders")
    purchase_order_count = fields.Integer(
            compute='_compute_purchase_order_count',
            string='# of Purchase Order')

    @api.one
    def _compute_purchase_order_count(self):
        procs = self.env['procurement.order'].search(
                [
                    ('sale_order_id', '=', self.id),
                    ('state', '!=', 'cancel')
                ])
        self.purchase_order_ids = procs.mapped('purchase_id')
        self.purchase_order_count = len(self.purchase_order_ids)

    @api.multi
    def action_confirm(self):
        self.ensure_one()
        res = super(SaleOrder, self).action_confirm()
        if res:
            self.action_confirm_purchase()
        return res

    @api.multi
    def action_confirm_purchase(self):
        self.ensure_one()
        _logger.debug("Confirm Related Purchases")
        for po in self.purchase_order_ids:
            _logger.debug("Confirming & Approving: %s", po.name)
            po.button_confirm()
        return True

    @api.multi
    def view_purchase_order(self):
        self.ensure_one()
        action = {}
        if self.purchase_order_ids.ids:
            form = self.env.ref(
                    'purchase.purchase_order_form')
            if len(self.purchase_order_ids.ids) > 1:
                tree = self.env.ref(
                        'purchase.purchase_order_tree')
                action.update({
                    'name': _('Purchase Orders'),
                    'view_mode': 'tree,form',
                    'views': [(tree.id, 'tree'), (form.id, 'form')],
                    'domain': [('id', 'in', self.purchase_order_ids.ids)],
                })
            else:
                action.update({
                    'name': _('Purchase Order'),
                    'view_mode': 'form',
                    'view_id': form.id,
                    'res_id': self.purchase_order_ids.ids[0],
                })
            action.update({
                'context': self._context,
                'view_type': 'form',
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
            })
        return action
