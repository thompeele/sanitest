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

import xmlrpclib
import logging
import urllib
from odoo import fields, models
from odoo import api

_logger = logging.getLogger(__name__)


class sale_order(models.Model):
    _inherit = "sale.order"

    magento_order = fields.Char(string='Magento Order', size=128)
    magento_status = fields.Char(string='Magento Status', size=128)
    auto_invoice = fields.Boolean(string='Automatic Invoice Creation')

    @api.multi
    def _prepare_invoice(self):
        """Inherit of the prepare invoice method to add the magento_order to the invoice values

           :param browse_record order: sale.order record to invoice
           :param list(int) line: list of invoice line IDs that must be
                                  attached to the invoice
           :return: dict of value to create() the invoice
        """

        return_vals = {}
        return_vals = super(sale_order, self)._prepare_invoice()
        return_vals['magento_order'] = self.magento_order

        return return_vals

    def process_magento_values(self, values):
        """
        Inheritable Method to parse the magento values passed to ODOO
        :param cr:
        :param uid:
        :param values: set of magento order values
        :param context:
        :return:
        """
        _logger.debug('Magento Create Order Values: %s', (values,))

        ext_delivery = "Download"

        if values.get('magento_shipping'):
            ext_delivery = values.get('magento_shipping')
            if ext_delivery == "":
                ext_delivery = "No Delivery Method"
            _logger.debug('Decoded Shipping string(UTF8): %s',
                          (urllib.unquote_plus(ext_delivery).decode('utf8'),))
            ext_delivery = urllib.unquote_plus(ext_delivery).decode('utf8')
            del values['magento_shipping']
        if values.get('magento_payment'):
            ext_payment = values.get('magento_payment')
            if ext_payment == "":
                ext_payment = "No Payment Method"
            del values['magento_payment']

        # Retreive Sales Team
        if values.get('mag_store_id'):
            #TODO: Check on current connection if more then 1 magento connection available
            _logger.debug('Magento Store ID provided: %s', values.get('mag_store_id'))
            magstore_obj = self.env['magento.store']
            magstores = magstore_obj.search([('store_id', '=', values.get('mag_store_id'))])
            for magstore in magstore_obj.browse(magstores.id):
                if magstore.sales_team_id:
                    values['team_id'] = magstore.sales_team_id.id
                    values['pricelist_id'] = magstore.pricelist_id.id
            del values['mag_store_id']

        matrix_obj = self.env['ext.order.matrix']
        values['pricelist_id'] = 1
        matrix_ids = matrix_obj.search(
            [('ext_delivery', '=', ext_delivery[:71]),
             ('ext_payment', '=', ext_payment), ],
        )

        if not(matrix_ids):
            matrix_vals = {
                'ext_delivery': ext_delivery[:71],
                'ext_payment': ext_payment,
            }
            matrix_id = matrix_obj.create(matrix_vals)
            matrix_ids = [matrix_id.id]
        else:
            matrix_ids = matrix_ids._ids

        matrix_values = matrix_obj.browse(matrix_ids).get_order_values()
        if matrix_values:
            values.update(matrix_values)

        return values


    @api.model
    def create_magento(self, values):
        """ Magento Create Order
        :param cr: cursor
        :param uid: user
        :param values: values passed by magento
        :param context:
        :return:
        """
        logging.info("::::::::::::::::::: %s"%values)
        if values:
            odoo_values = self.process_magento_values(values)
            if odoo_values:
                return self.create(odoo_values).id
        return 0

    # to do  still waiting for magento invoice cancel.......
    def manual_magento_order_cancel(self):
        text = ''
        status = 'no'
        self.env = api.Environment()
        connection = self.env['magento.configure']._create_connection()
        if connection:
            server = xmlrpclib.Server(connection[0])
            map_id = self.env['magento.orders'].search([(
                'oe_order_id', '=', self._ids[0])])
            if map_id:
                map_obj = self.env['magento.orders'].browse(map_id[0].id)
                increment_id = map_obj.mag_orderIncrement_Id
                self.env['magento.orders'].release_mage_order_from_hold(increment_id, connection)
                try:
                    server.call(connection[1], 'sales_order.cancel', [increment_id])
                    text = 'sales order %s has been sucessfully canceled from magento.' % map_obj.order_ref.name
                    status = 'yes'
                except Exception, e:
                    text = 'Order %s cannot be canceled from magento, Because Magento order %s is in different state.' % (
                        map_obj.order_ref.name, map_obj.mag_orderIncrement_Id)
            else:
                text = 'Order cannot be canceled from magento, cause %s order is created from openerp.' % self._ids[0]
        self.env['magento.sync.history'].create({'status': status,
                                                 'action_on': 'order',
                                                 'action': 'b',
                                                 'error_message': text})

    def action_cancel(self):
        return_value = super(sale_order, self).action_cancel()
        if return_value:
            self.manual_magento_order_cancel()
        return return_value

    def magento_ship_trigger(self):
        for sale_id in self._ids:
            config_id = self.env['magento.configure'].search([('active', '=', True), ('auto_ship', '=', True)])
            if len(config_id.id) == 1:
                order_name = self.sale_id.name
                if order_name:
                    self._cr.commit()
                    self.manual_magento_shipment(order_name)
        return True

    def manual_magento_shipment(self, order_name):
        text = ''
        status = 'no'
        mage_shipment = False
        self.env = api.Environment()
        connection = self.env['magento.configure']._create_connection()
        if connection and self._ids:
            server = xmlrpclib.Server(connection[0])
            map_id = self.env['magento.orders'].search([('oe_order_id', 'in', self._ids)])
            if map_id:
                map_obj = self.env['magento.orders'].browse(map_id[0].id)
                increment_id = map_obj.mag_orderIncrement_Id
                h = self.env['magento.orders'].release_mage_order_from_hold(increment_id, connection)
                try:
                    ship_array = [increment_id, [], 'Shipped from ODOO', True]
                    mage_shipment = server.call(connection[1], 'order_shipment.create', ship_array)
                    text = 'shipment of order %s has been successfully updated on magento.' % order_name
                    status = 'yes'
                except xmlrpclib.Fault, e:
                    if e.faultCode == 103:
                        text = 'shipment of order %s cannot be done on magento. Because order %s does not exist on Magento.' % (
                            order_name, increment_id)
                    else:
                        text = 'shipment of order %s has been already updated on magento.' % order_name
                        status = 'yes'
            else:
                text = 'Order cannot be shipped from magento, Cause %s order is created from openerp.' % order_name
        self._cr.commit()
        self.env['magento.sync.history'].create({'status': status,
                                                 'action_on': 'order',
                                                 'action': 'b',
                                                 'error_message': text})
        return mage_shipment


sale_order()
