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

import urllib
import logging
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    magento_transport = fields.Char(
            string='Magento Transport',
            size=128
    )

    @api.model
    def _prepare_procurement_group(self):
        res = super(SaleOrder, self)._prepare_procurement_group()
        if res and self.magento_transport:
            res['magento_transport'] = self.magento_transport
        return res

    @api.multi
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if res and self.magento_transport:
            res['magento_transport'] = self.magento_transport
        return res

    @api.model
    def process_magento_values(self, values):
        if values.get('magento_shipping'):
            ext_delivery = values.get('magento_shipping')
            if ext_delivery == "":
                ext_delivery = "No Delivery Method"
            _logger.debug('Decoded Shipping string(UTF8): %s',
                          (urllib.unquote_plus(ext_delivery).decode('utf8'),))
            ext_delivery = urllib.unquote_plus(ext_delivery).decode('utf8')
            if ext_delivery:
                values['magento_transport'] = ext_delivery

        return super(SaleOrder, self).process_magento_values(values)
