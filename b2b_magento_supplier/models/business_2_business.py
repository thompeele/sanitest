# -*- encoding: utf-8 -*-

import xmlrpclib
import logging
import urllib
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class Business2BusinessMagento(models.Model):
    _inherit = "business.2.business"

    @api.model
    def _process_order_values(self, values, partner):
        """
       Inheritable Method to parse the magento values passed to ODOO
       :param cr:
       :param uid:
       :param values: set of magento order values
       :param context:
       :return:
       """
        _logger.debug('B2B Process Order Values: %s', values)
        order_values = {}
        order_values['partner_id'] = partner.id
        if values.get('OrderRef'):
            order_values['client_order_ref'] = values.get('OrderRef')
        if values.get('MagOrderRef'):
            order_values['magento_order_ext'] = values.get('MagOrderRef')
        order_values['section_id'] = self.section_id.id
        order_values['pricelist_id'] = self.partner_id.property_product_pricelist.id or self.pricelist_id.id
        if values.get('Address'):
            dropship_address = self.env['dropship.address'].create_address(values.get('Address'))
            if dropship_address:
                order_values['dropship_address'] = dropship_address.id
        return order_values