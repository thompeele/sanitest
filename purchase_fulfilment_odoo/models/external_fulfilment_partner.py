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

class ExternalFulfilmentPartner(models.Model):
    _inherit = 'external.fulfilment.partner'

    @api.multi
    def fulfil_orderlist_state(self):
        self.ensure_one()
        res = super(ExternalFulfilmentPartner, self).fulfil_orderlist_state()
        if self.external_fulfilment.type == 'odoo':
            odoo = self.external_fulfilment.connection.connect()
            order_list = self.prepare_external_order_list()
            _logger.debug('Send List: %s', order_list)
            if odoo and order_list:
                return_list = odoo.model('business.2.business').request_orderlist_state(order_list)
                _logger.debug('Received List: %s', return_list)
                if return_list.get('orderlist'):
                    for order in return_list.get('orderlist'):
                        _logger.debug('Process Order: %s', order)
                        self.process_order_state(order)
        return res

    @api.multi
    def fulfil_product_sync(self):
        self.ensure_one()
        res = super(ExternalFulfilmentPartner, self).fulfil_product_sync()
        if self.external_fulfilment.type == 'odoo':
            odoo = self.external_fulfilment.connection.connect()
            if not odoo:
                _logger.error("Error connecting to External ODOO")
                return res
            values = {}
            values['CustomerRef'] = self.external_id
            values['Product'] = False
            return_productlist = odoo.model(
                    'business.2.business'
            ).request_product_data(values)
            _logger.debug('Received Response: %s', return_productlist)

            if return_productlist.get('productlist'):
                confirmedsync = []
                for external_product in return_productlist.get('productlist'):
                    feedback_id = self.process_product(
                            external_product.get('product')
                    )
                    if feedback_id:
                        confirmedsync.append(feedback_id)
                _logger.debug("Confirm Sync: %s", confirmedsync)
                self.fulfil_product_sync_confirm(confirmedsync)
        return res

    @api.multi
    def fulfil_product_map(self):
        self.ensure_one()
        res = super(ExternalFulfilmentPartner, self).fulfil_product_map()
        if self.external_fulfilment.type == 'odoo':
            odoo = self.external_fulfilment.connection.connect()
            if odoo:
                odoo.model('business.2.business').map_product_data(res)
        return True

    @api.model
    def fulfil_product_sync_confirm(self, list):
        self.ensure_one()
        res = super(ExternalFulfilmentPartner, self).fulfil_product_sync_confirm(list)
        if self.external_fulfilment.type == 'odoo':
            odoo = self.external_fulfilment.connection.connect()
            if odoo:
                odoo.model('business.2.business').confirmsync(list)