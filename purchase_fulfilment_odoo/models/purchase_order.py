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

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def fulfil_send_order(self):
        self.ensure_one()
        external_id, external_state = super(PurchaseOrder, self).fulfil_send_order()
        if self.external_fulfilment_partner.external_fulfilment.type == 'odoo':
            _logger.debug("Send Order to ODOO")
            odoo = self.external_fulfilment_partner.external_fulfilment.connection.connect()
            order_vals = self.prepare_external_send_order_values()
            _logger.debug('Send Order Values: %s', order_vals)
            res = odoo.model('business.2.business').receive_order(order_vals)
            _logger.debug('Received Response: %s', res)
            if res.get('order'):
                order = res.get('order')
                external_id = order.get('ref')
                external_state = 'processing'
            if res.get('error'):
                error = res.get('error')
                external_state = 'Error: %s (%s)' % (error.get('message'), error.get('code'))

        return external_id, external_state

    @api.multi
    def fulfil_cancel_order(self):
        self.ensure_one()
        external_state, cancel_succesfull = super(PurchaseOrder, self).fulfil_cancel_order()

        if self.external_fulfilment_partner.external_fulfilment.type == 'odoo':
            _logger.debug("Cancel Order to ODOO: %s", self.name)
            odoo = self.external_fulfilment_partner.external_fulfilment.connection.connect()
            cancel_vals = self.prepare_external_cancel_order_values()
            _logger.debug(cancel_vals)
            res = odoo.model('business.2.business').cancel_order(cancel_vals)
            _logger.debug('Received Response: %s', res)
            if res.get('order'):
                _logger.debug('Set sate canceled')
                external_state = 'Cancelled'
                cancel_succesfull = True
            if res.get('error'):
                error = res.get('error')
                external_state = 'Error: %s (%s)' % (error.get('message'), error.get('code'))
                cancel_succesfull = False

        return external_state, cancel_succesfull
