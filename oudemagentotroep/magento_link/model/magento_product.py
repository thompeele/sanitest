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

import logging
from odoo import fields, models, api
import urllib


_logger = logging.getLogger(__name__)


class magento_product(models.Model):
    _name = "magento.product"
    _order = 'id desc'
    _rec_name = "pro_name"
    _description = "Magento Product"

    pro_name = fields.Many2one('product.product', string='Product Name')
    oe_product_id = fields.Integer(string='Openerp Product Id')
    mag_product_id = fields.Integer(string='Magento Product Id')
    need_sync = fields.Selection([('Yes', 'Yes'),
                                  ('No', 'No')],
                                 string='Update Required')
    create_date = fields.Datetime(string='Created Date')
    write_date = fields.Datetime(string='Updated Date')

    _defaults = {
        'need_sync': 'No',
    }

    @api.model
    def _magento_get_product_type(self, type):
        """
        Get corresponding ODOO Type
        :param cr:
        :param uid:
        :param type: magento type
        :param context:
        :return: magento.product.type object
        """

        pt_pool = self.env['magento.product.type']
        pt_ids = pt_pool.search([('name', '=', type)])
        if not pt_ids:
            pt_id = pt_pool.create({'name': type, 'odoo_type': 'consu'})
        else:
            pt_id = pt_ids[0]

        pt_obj = pt_id
        return pt_obj

    @api.model
    def _magento_product_store_update(self, storeview_data, product_id):
        """
        Method to update the values of store specific data in ODOO,
        reusing the map_product_valuoes
        :param cr: current cursor
        :param uid: current user
        :param storeview_data: storeview_data
        :param product_id: odoo product id
        :param context: current context
        :return: True or False
        """

        _logger.debug("Store Product Data: %s", (storeview_data))
        product_id = self.env['product.product'].browse(product_id)
        for data in storeview_data:
            _logger.debug("Store specific values: %s", (storeview_data[data]))
            store_data = self._magento_map_product_values(storeview_data[data],
                                                          ['store', 'data'])
            store_text_data = self._magento_map_product_values(storeview_data[data],
                                                               ['store', 'store-text'])
            _logger.debug("Store specific values: %s", (store_data))
            for store in self.env['magento.store'].search([('store_id', '=', data)]):

                ps_pool = self.env['product.product.magento.store']
                ps_ids = ps_pool.search([('product_id', '=', product_id.id),
                                         ('store_id', '=', store.store_id)])
                if ps_ids:
                    ps_pool.browse(ps_ids.id).write(store_data)
                else:
                    store_create_data = store_data.copy()
                    store_create_data.update({'product_id': product_id.id,
                                              'store_id': store.store_id})
                    ps_pool.create(store_create_data)

                # Update Text Fields
                context_store = self._context.copy()
                if store.lang:
                    context_store.update({'lang': store.lang})
                product_id.write(store_text_data)
        return True

    @api.multi
    def _magento_map_product_values(self, data, request_list):
        _logger.debug('Incoming Data to Map: %s', data)
        if not isinstance(request_list, list):
            request_list = [request_list]

        odoo_values = {}

        if 'text' in request_list or 'all' in request_list:
            if data.get('name'):
                odoo_values['name'] = urllib.unquote_plus(data.get('name').encode('utf8'))
            if data.get('default_code'):
                odoo_values['default_code'] = urllib.unquote_plus(data.get('default_code').encode('utf8'))
            if data.get('description'):
                odoo_values['description'] = urllib.unquote_plus(data.get('description').encode('utf8'))
            if data.get('short_description'):
                odoo_values['short_description'] = urllib.unquote_plus(data.get('short_description').encode('utf8'))

        if 'store-text' in request_list:
            if data.get('name'):
                odoo_values['name'] = urllib.unquote_plus(data.get('name').encode('utf8'))
            if data.get('description'):
                odoo_values['description'] = urllib.unquote_plus(data.get('description').encode('utf8'))
            if data.get('short_description'):
                odoo_values['short_description'] = urllib.unquote_plus(data.get('short_description').encode('utf8'))

        if 'data' in request_list or 'all' in request_list:

            if data.get('image'):
                odoo_values['image'] = data.get('image')
            if data.get('ean13'):
                odoo_values['barcode'] = data.get('ean13')

            # Special Price
            if data.get('special_price'):
                odoo_values['special_price'] = data.get('special_price')
            if data.get('special_from_date'):
                odoo_values['special_from'] = data.get('special_from_date')
            if data.get('special_to_date'):
                odoo_values['special_to'] = data.get('special_to_date')

            # New
            if data.get('news_from_date'):
                odoo_values['new_from'] = data.get('news_from_date')
            if data.get('news_to_date'):
                odoo_values['new_to'] = data.get('news_to_date')

            # Custom Design
            if data.get('custom_design_from'):
                odoo_values['custom_design_from'] = data.get('custom_design_from')
            if data.get('custom_design_to'):
                odoo_values['custom_design_to'] = data.get('custom_design_to')

            # Meta Info
            if data.get('meta_keyword'):
                odoo_values['meta_keyword'] = urllib.unquote_plus(data.get('meta_keyword').encode('utf8'))
            if data.get('meta_title'):
                odoo_values['meta_title'] = urllib.unquote_plus(data.get('meta_title').encode('utf8'))
            if data.get('meta_description'):
                odoo_values['meta_description'] = urllib.unquote_plus(data.get('meta_description').encode('utf8'))

            # Url Info
            if data.get('url_key'):
                odoo_values['url_key'] = data.get('url_key').encode('utf8')
            if data.get('url_path'):
                odoo_values['url_path'] = data.get('url_path').encode('utf8')

            # Store Specific Price
            if data.get('price'):
                odoo_values['price'] = data.get('price') or 0.0

            # Magento Visible
            if data.get('visibility'):
                odoo_values['magento_visible'] = data.get('visibility')

        if 'all' in request_list:
            # Type
            if data.get('type'):
                mag_type = self._magento_get_product_type(data.get('type'))
                odoo_values['type'] = mag_type.odoo_type
                odoo_values['magento_type'] = mag_type.id
            # Prices
            odoo_values['list_price'] = data.get('list_price') or 0.00
            odoo_values['lst_price'] = data.get('list_price') or 0.00

            if data.get('standard_price'):
                odoo_values['standard_price'] = data.get('standard_price')

            # Weight
            if data.get('weight') and data.get('weight_net'):
                odoo_values['weight'] = data.get('weight')
                odoo_values['weight'] = data.get('weight_net')
            elif data.get('weight') and not data.get('weight_net'):
                odoo_values['weight'] = data.get('weight')
            elif not data.get('weight') and data.get('weight_net'):
                odoo_values['weight'] = data.get('weight_net')
            else:
                odoo_values['weight'] = 0.0

            if data.get('standard_price'):
                odoo_values['standard_price'] = data.get('standard_price')

            # Product Categories
            if data.get('categ_ids'):
                public_categ_ids = data.get('categ_ids')
                odoo_values['public_categ_ids'] = [(6, 0, public_categ_ids)]

        _logger.debug('Mapped Values: %s', odoo_values)

        return odoo_values

    @api.multi
    def _magento_remove_value_write(self, product_values):
        """
        Remove Values for Write
        :param product_values:
        :return: product_values:
        """
        if product_values.get('type'):
            del product_values['type']

        return product_values

    def _magento_remove_value_create(self, product_values):
        """
        Remove Values for Write
        :param product_values:
        :return: product_values:
        """
        return product_values

    @api.model
    def create_product(self, data):
        """
        Create Product in database by passing values
        :param cr: cursor
        :param uid: current user
        :param data: passed data {}
        :param context: current context
        :return: product_id
        """
        # Parse the received data and create a new set of values
        product_values = self._magento_map_product_values(data, ['product', 'all'])
        storeview_data = data.get('storeview_data')

        # Check if mapping for product already exists
        mag_product_id = data.get('mage_id')
        mag_prod_ids = self.search([('mag_product_id', '=', mag_product_id)])
        # Update Text Fields
        ctx_conn = self._context.copy()
        conn_ids = self.env['magento.configure'].search([])

        if conn_ids:
            ## TODO: Determine a way to get the correct connection, shared secret?
            conn = conn_ids[0]
            ctx_conn.update({'lang': conn.lang})

        if mag_prod_ids:
            for mag_prod in mag_prod_ids:
                _logger.debug('Product write: Magento ID: %s, ODOO Product ID: %s',
                              str(mag_product_id), str(mag_prod.oe_product_id))
                product_values = self._magento_remove_value_write(product_values)

                self.env['product.product'].browse(mag_prod.oe_product_id).write(product_values)
                if storeview_data:
                    self._magento_product_store_update(storeview_data,
                                                       mag_prod.oe_product_id)
                                                        #self._context=ctx_conn)
                return mag_prod.oe_product_id
        else:
            _logger.debug('Product create for Magento ID: %s',
                          str(data.get('mage_id')))

            product_values = self._magento_remove_value_create(product_values)

            product_id = self.env['product.product'].create(product_values)

            if storeview_data:
                self._magento_product_store_update(storeview_data,
                                                   product_id.id)
                                                   #self._context=ctx_conn)
            self.create({'pro_name': product_id.id,
                         'oe_product_id': product_id.id,
                         'mag_product_id': mag_product_id,
                         'need_sync': 'No'})
            return product_id.id
        return False
magento_product()
