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
import time
#import odoo.netsvc
from odoo.tools.translate import _
#from xmlrpclib import *
import xmlrpclib
import openerp.tools
import urllib
from odoo import workflow, models, fields, api
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class magento_synchronization(models.Model):
    _name = "magento.synchronization"

    @api.multi
    def open_configuration(self):
        """
        Open a magento configuration / connection
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return:
        """
        view_id = False
        setting_ids = self.env['magento.configure'].search(
            [
                ('active', '=', True)
            ]
        )
        if setting_ids:
            view_id = setting_ids[0].id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configure Magento Api',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'magento.configure',
            'res_id': view_id,
            'target': 'current',
            'domain': '[]',
        }

    @api.model
    def _update_specific_category(self, id, connection):
        """
        Update Specific Category
        :param cr:
        :param uid:
        :param id:
        :param connection:
        :param context:
        :return:
        """
        get_category_data = {}
        cat_up = False
        cat_mv = False
        cat_pool = self.env['magento.category']
        cat_obj = cat_pool.browse(id)
        cat_id = cat_obj.oe_category_id
        mage_id = cat_obj.mag_category_id
        mag_parent_id = 1

        if cat_id and mage_id:
            obj_cat = self.env['product.public.category'].browse(cat_id)

            get_category_data['name'] = obj_cat.name
            get_category_data['available_sort_by'] = 1
            get_category_data['default_sort_by'] = 1

            parent_id = obj_cat.parent_id.id or False

            if parent_id:
                search = cat_pool.search(
                    [
                        ('cat_name', '=', parent_id)
                    ]
                )

                if search:
                    mag_parent_id = search[0].mag_category_id or 1
                else:
                    mag_parent_id = self.sync_categories(connection, parent_id)
            update_data = [mage_id, get_category_data]
            move_data = [mage_id, mag_parent_id]
            try:
                server = xmlrpclib.Server(connection[0])
                cat = server.call(
                    connection[1],
                    'catalog_category.update',
                    update_data
                )
                cat_mv = server.call(
                    connection[1],
                    'catalog_category.move',
                    move_data
                )
                cat_obj.write({'need_sync': 'No'})
            except xmlrpclib.Fault, e:
                return [0, str(e)]
            except Exception, e:
                return [0, str(e)]
            return [1, cat_id]

    @api.multi
    def update_categories_button(self):
        self.update_categories()

    @api.model
    def update_categories(self):
        """
        Update Product Categories
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return:
        """
        text = text1 = ''
        up_error_ids = []
        success_ids = []

        # Get 8.0 API environment
        connection = self.env['magento.configure']._create_connection()
        if connection:
            map_id = self.env['magento.category'].search(
                [
                    ('need_sync', '=', 'Yes')
                ]
            )

            if not map_id:
                raise UserError(_("No category(s) has been found to be Update on Magento!!!"))
            if map_id:
                for i in map_id:
                    cat_update = self._update_specific_category(
                        i.id,
                        connection
                    )

                    if cat_update[0] != 0:
                        success_ids.append(cat_update[1])
                    else:
                        up_error_ids.append(cat_update[1])

                if success_ids:
                    text = 'List of %s Category ids has been sucessfully updated to Magento. \n' % success_ids
                    self.env['magento.sync.history'].create(
                        {
                            'status': 'yes',
                            'action_on': 'category',
                            'action': 'c',
                            'error_message': text
                        }
                    )

                if up_error_ids:
                    text1 = 'The Listed Category ids %s does not updated on Magento.' % up_error_ids

                    self.env['magento.sync.history'].create(
                        {
                            'status': 'no',
                            'action_on': 'category',
                            'action': 'c',
                            'error_message': text1
                        }
                    )

                partial = self.env['message.wizard'].create(
                    {'text': text + text1}
                )

                return {
                    'name': _("Information"),
                    'view_mode': 'form',
                    'view_id': False,
                    'view_type': 'form',
                    'res_model': 'message.wizard',
                    'res_id': partial.id,
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                    'domain': '[]',
                }

    @api.model
    def create_category(self, connection, catg_id,
                        parent_id, catgname):
        """
        Create Product Category
        :param cr:
        :param uid:
        :param connection:
        :param catg_id:
        :param parent_id:
        :param catgname:
        :param context:
        :return:
        """
        cat = parent_id
        server = xmlrpclib.Server(connection[0])
        catgdetail = dict(
            {
                'name': catgname,
                'is_active': 1,
                'available_sort_by': 1,
                'default_sort_by': 1,
                'is_anchor': 1,
                'include_in_menu': 1
            }
        )

        if catg_id > 0:
            updatecatg = [parent_id, catgdetail]
            try:
                cat = server.call(
                    connection[1],
                    'catalog_category.create',
                    updatecatg
                )
            except xmlrpclib.Fault, e:
                return 0
        else:
            return False
        if cat > 0:
            # ODOO Mapping Entry
            mapping_values = {
                'cat_name': catg_id,
                'oe_category_id': catg_id,
                'mag_category_id': cat,
                'need_sync': 'No'
            }
            self.env['magento.category'].create(mapping_values)

            self._cr.commit()
            # Magento mapping Entry
            ##TODO: Trigger on mapping ODOO create ?
            server.call(
                connection[1],
                'odoolink.category_map',
                [
                    {'mage_category_id': cat, 'erp_category_id': catg_id}
                ]
            )

            return cat

    @api.multi
    def sync_categories(self, connection, cat_id):
        """
        Synchronise Product Categories
        :param cr:
        :param uid:
        :param connection:
        :param cat_id:
        :param context:
        :return:
        """
        check = self.env['magento.category'].search(
            [
                ('oe_category_id', '=', cat_id)
            ]
        )
        if not check:
            obj_catg = self.env['product.public.category'].browse(
                cat_id
            )

            name = obj_catg.name
            if obj_catg.parent_id.id:
                p_cat_id = self.sync_categories(
                    connection,
                    obj_catg.parent_id.id
                )
            else:
                p_cat_id = self.create_category(
                    connection,
                    obj_catg.id,
                    1,
                    name
                )
                return p_cat_id

            category_id = self.create_category(
                connection,
                obj_catg.id,
                p_cat_id,
                name
            )
            return category_id
        else:
            mage_id = check[0].mag_category_id

            return mage_id

    @api.multi
    def export_categories(self):
        catg_map = {}
        map_dic = []
        length = 0
        connection = self.env['magento.configure']._create_connection()

        if connection:
            map_id = self.env['magento.category'].search([])
            for m in map_id:
                map_obj = self.env['magento.category'].browse(m.id)
                map_dic.append(map_obj.oe_category_id)
                catg_map[map_obj.oe_category_id] = map_obj.mag_category_id

            erp_catg = self.env['product.public.category'].search(
                [
                    ('id', 'not in', map_dic)
                ]
            )

            if not erp_catg:
                raise UserError(
                    _("All category(s) has been already exported on magento.")
                )

            for l in erp_catg:
                cat_id = self.sync_categories(
                    connection,
                    l
                )
                length += 1

            text = "%s category(s) has been Exported to magento." % (length)

            self.env['magento.sync.history'].create(
                {
                    'status': 'yes',
                    'action_on': 'category',
                    'action': 'b',
                    'error_message': text
                }
            )

            partial = self.env['message.wizard'].create(
                {'text': text}
            )

            return {
                'name': _("Information"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'message.wizard',
                'res_id': partial.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
            }

    @api.model
    def export_bulk_category(self):
        text = ''
        text1 = text2 = ''
        fail_ids = []
        error_ids = []
        up_error_ids = []
        success_up_ids = []
        success_exp_ids = []
        bulk_ids = self._context.get('active_ids')
        map_obj = self.env['magento.category']
        connection = self.env['magento.configure']._create_connection()
        if connection:
            for l in bulk_ids:
                search = map_obj.search([('cat_name', '=', l)])
                if not search:
                    cat_id = self.sync_categories(
                        connection,
                        l
                    )

                    if cat_id:
                        success_exp_ids.append(l)
                else:
                    map_id = self.env['magento.category'].browse(search[0].id)

                    if map_id.need_sync == 'Yes':
                        cat_update = self._update_specific_category(
                            map_id.id,
                            connection,
                        )

                        if cat_update[0] != 0:
                            success_up_ids.append(l)
                        else:
                            up_error_ids.append(cat_update[1])
                    else:
                        fail_ids.append(l)

            if success_exp_ids:
                text = "\nThe Listed category ids %s has been created on magento." % (success_exp_ids)
            if fail_ids:
                text += "\nSelected category ids %s are already synchronized on magento." % (fail_ids)
            if text:
                self.env['magento.sync.history'].create(
                    {
                        'status': 'yes',
                        'action_on': 'product',
                        'action': 'b',
                        'error_message': text
                    }
                )

            if success_up_ids:
                text1 = '\nThe Listed category ids %s has been successfully updated to Magento. \n' % success_up_ids
                self.env['magento.sync.history'].create(
                    {
                        'status': 'yes',
                        'action_on': 'product',
                        'action': 'c',
                        'error_message': text1
                    }
                )

            if up_error_ids:
                text2 = '\nThe Listed category ids %s does not updated on magento.' % up_error_ids
                self.env['magento.sync.history'].create(
                    {
                        'status': 'no',
                        'action_on': 'product',
                        'action': 'c',
                        'error_message': text2
                    }
                )

            partial = self.env['message.wizard'].create(
                {
                    'text': text + text1 + text2
                }
            )

            return {
                'name': _("Information"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'message.wizard',
                'res_id': partial.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
            }

    @api.multi
    def update_products(self):

        text = text1 = ''
        up_error_ids = []
        success_ids = []

        connection = self.env['magento.configure']._create_connection()
        if connection:
            server = xmlrpclib.Server(connection[0])
            map_ids = self.env['magento.product'].search(
                [
                    ('need_sync', '=', 'Yes')
                ]
            )
            pro_ids = self.env['product.product'].search([], count=True)
            for product in map_ids:
                if not product or not pro_ids:
                    raise UserError(
                        _("No product(s) has been found to be Update on Magento!!!")
                    )

                if product:

                    if not product.oe_product_id or not self.env['product.product'].browse(product.oe_product_id).magento_send:
                        continue

                    for i in self.env['magento.product'].browse(
                            product.id
                    ):
                        _logger.debug('Update the following magento product: %s', i)
                        pro_update = self._update_specific_product(
                            i,
                            connection,
                        )
                        if pro_update[0] != 0:
                            success_ids.append(pro_update[1])
                        else:
                            up_error_ids.append(pro_update[1])

                        if connection[2].product_sync_delay:
                            _logger.debug(
                                "Product Sync Delay: %s",
                                connection[2].product_sync_delay
                            )
                            time.sleep(connection[2].product_sync_delay)
                        else:
                            _logger.debug("No sync delay")

                    if success_ids:
                        text = 'The Listed Product ids %s has been sucessfully updated to Magento. \n' % success_ids
                        self.env['magento.sync.history'].create(
                            {
                                'status': 'yes',
                                'action_on': 'product',
                                'action': 'c', 'error_message': text
                            }
                        )

                    if up_error_ids:
                        text1 = 'The Listed Product ids %s does not updated on magento.' % up_error_ids
                        self.env['magento.sync.history'].create(
                            {
                                'status': 'no',
                                'action_on': 'product',
                                'action': 'c',
                                'error_message': text1
                            }
                        )

                    text2 = text + text1

                    if not text2:
                        raise UserError(
                            _("No product(s) has been found to be Update on Magento!!!")
                        )

                    partial = self.env['message.wizard'].create(
                        {
                            'text': text2
                        }
                    )

                    return {
                        'name': _("Information"),
                        'view_mode': 'form',
                        'view_id': False,
                        'view_type': 'form',
                        'res_model': 'message.wizard',
                        'res_id': partial.id,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]',
                    }

    @api.multi
    def _get_product_categories(self, connection, product):
        """
        Get the product categories of single product
        :param cr: current cursor
        :param uid: current user
        :param connection: current connection
        :param product: product object
        :param context: current context
        :return: list of categorie ids []
        """

        return_categories = []

        #Link with magento product categories
        for category in product.public_categ_ids:
            mage_categ_id = self.sync_categories(
                connection,
                category.id,
            )
            return_categories.append(mage_categ_id)

        return return_categories

    @api.multi
    def _get_magento_product_values(self, listvalues):
        product = listvalues[0]
        categories = listvalues[1]
        connection = listvalues[2][2]
        method = listvalues[3]

        product_values = {
            'name': product.name,
            'price': product.list_price or 0.00,
            'weight': product.weight or 0.00,
            'categories': categories,
            'ean': product.barcode or False
        }

        if product.special_price:
            product_values['special_price'] = product.special_price
        if product.special_from:
            product_values['special_from_date'] = product.special_from
        if product.special_to:
            product_values['special_to_date'] = product.special_to

        if method == 'create':
            if product.short_description:
                product_values['short_description'] = product.short_description
            if product.description:
                product_values['description'] = product.description
            if product.meta_title:
                product_values['meta_title'] = product.meta_title
            if product.meta_keyword:
                product_values['meta_keyword'] = product.meta_keyword
            if product.meta_description:
                product_values['meta_description'] = product.meta_description
            if product.new_from:
                product_values['news_from_date'] = product.new_from
            if product.new_to:
                product_values['news_to_date'] = product.new_to
            if product.url_key:
                product_values['url_key'] = product.url_key
            if product.url_path:
                product_values['url_path'] = product.url_path
            if product.custom_design:
                product_values['custom_design'] = product.custom_design
            if product.custom_design_from:
                product_values['custom_design_from'] = product.custom_design_from
            if product.custom_design_to:
                product_values['custom_design_to'] = product.custom_design_to

        websites = []
        if product.store_ids:

            for store in product.store_ids:
                if store.store_id.website_id and store.store_id.website_id not in websites and store.store_id in connection.store_ids:
                    websites.append(store.store_id.website_id)

        product_values['websites'] = websites
        return product_values

    @api.multi
    def _get_magento_store_product_values(self, listvalues):
        ''' Get the product data of single product
        :param cr: current cursor
        :param uid: current user
        :param product: product object
        :param store: magento store
        :param context: current context
        :return: dict with product data
        '''

        product = listvalues[0]
        store = listvalues[1]
        method = listvalues[2]

        ##TODO: Get price from defined pricelist on store or use the overruling with defined price
        #store_price = store.pricelist_id.price_get()
        prodmag_pool = self.env['product.product.magento.store']
        prodmag_ids = prodmag_pool.search([('product_id', '=', product.id),('store_id', '=', store.id)])

        if prodmag_ids:
            prodmag = prodmag_ids[0]

            context_store = self._context.copy()
            if prodmag.store_id.lang:
                context_store.update({'lang': prodmag.store_id.lang})

            store_product = self.env['product.product'].browse(product.id)[0]

            product_values = {}

            if prodmag.special_price:
                product_values['special_price'] = prodmag.special_price
            if prodmag.special_from:
                product_values['special_from_date'] = prodmag.special_from
            if prodmag.special_to:
                product_values['special_to_date'] = prodmag.special_to

            if prodmag.price:
                product_values['price'] = prodmag.price
            else:
                product_values['price'] = product.list_price

            if store_product.name:
                product_values['name'] = store_product.name

            if method == 'create':
                if store_product.short_description:
                    product_values['short_description'] = store_product.short_description
                if store_product.description:
                    product_values['description'] = store_product.description
                if prodmag.meta_title:
                    product_values['meta_title'] = prodmag.meta_title
                if prodmag.meta_keyword:
                    product_values['meta_keyword'] = prodmag.meta_keyword
                if prodmag.meta_description:
                    product_values['meta_description'] = prodmag.meta_description
                if prodmag.new_from:
                    product_values['news_from_date'] = prodmag.new_from
                if prodmag.new_to:
                    product_values['news_to_date'] = prodmag.new_to
                if prodmag.url_key:
                    product_values['url_key'] = prodmag.url_key
                if prodmag.url_path:
                    product_values['url_path'] = prodmag.url_path
                if prodmag.custom_design:
                    product_values['custom_design'] = prodmag.custom_design
                if prodmag.custom_design_from:
                    product_values['custom_design_from'] = prodmag.custom_design_from
                if prodmag.custom_design_to:
                    product_values['custom_design_to'] = prodmag.custom_design_to

            return product_values
        return False

    @api.multi
    def _magento_update_product(
            self, connection, magento_id, values, product_id=False, store_id=False):
        """ Update Magento Values with provided values
        :param cr: current cursor
        :param uid: current user
        :param connection: current connection
        :param magento_id: magento product id
        :param values: provided values
        :param product_id: odoo product id
        :param store_id: magento store id
        :param context: current context
        :return: list [0/1, Message]
        """
        _logger.debug('Magento Update: %s', magento_id)
        server = xmlrpclib.Server(connection[0])

        try:
            if store_id:
                magento_update = [magento_id, values, store_id]
            else:
                magento_update = [magento_id, values]

            server.call(connection[1], 'product.update', magento_update)
            if product_id:  # If product_id then it's an update
                map_ids = self.env['magento.product'].search([('mag_product_id', '=', magento_id)])
                _logger.debug('Updating Mapping to No Update: %s', map_ids)
                map_ids.write({'need_sync': 'No'})
                self._cr.commit()
            else:
                #TODO
                _logger.debug("Could do a create here")

            return [1, False]
        except xmlrpclib.Fault, e:
            _logger.debug('Error updating product on magento server')
            return [0, str(e)]

        return [0, False]

    @api.multi
    def _magento_update_product_stock(self, connection, magento_id, values):

        server = xmlrpclib.Server(connection[0])

        try:
            server.call(connection[1], 'product_stock.update', [magento_id, values])
            return True
        except:
            return False

    @api.multi
    def _get_magento_product_stock_values(self, product):

        stock_values = {}
        stock_values['manage_stock'] = 1

        current_stock = product.qty_available - product.outgoing_qty
        if current_stock > 0:
            stock_values['qty'] = current_stock
        else:
            stock_values['qty'] = 0

        return stock_values

    @api.multi
    def _update_specific_product(self, magprod, connection):
        """Update Specific Product
        :param cr: cursor
        :param uid: user
        :param mag_prod: magento product object
        :param connection: current connection
        :param context:
        :return:
        """

        odoo_id = magprod.oe_product_id
        magento_id = magprod.mag_product_id
        if magento_id and odoo_id:
            prod_catg = []
            quantity = 0
            stock = 1
            product = self.env['product.product'].browse(odoo_id)
            # Get product categories
            prod_catg = self._get_product_categories(connection, product)

            # Get product data
            list_values = [product, prod_catg, connection, 'update']

            get_product_data = self._get_magento_product_values(
                list_values
            )

            return_update_product = self._magento_update_product(connection, magento_id, get_product_data, product_id=odoo_id)
            if connection[2].store_ids:
                _logger.debug('Browse Stores')
                for store in connection[2].store_ids:
                    _logger.debug('Current Store: %s', store.id)
                    # Get Store View Product Data
                    if not(store.active):
                        _logger.debug('Store inactive: %s', store.id)
                        break
                    get_store_product_data = self._get_magento_store_product_values([product, store, 'update'])
                    _logger.debug('Product Data: %s', get_store_product_data)
                    if get_store_product_data:
                        # Extra Update so don't pass the product_id
                        self._magento_update_product(connection, magento_id, get_store_product_data, store_id=store.store_id)
            if return_update_product[0] == 1:
                # Update product stock on magento
                stock_values = self._get_magento_product_stock_values(product)
                self._magento_update_product_stock(connection, magento_id, stock_values)

                # Update product images on magento
                if connection[2].product_update_image:
                    self.prodimage(connection, product, magento_id)
                return [1, odoo_id]
            else:
                return [0, str(odoo_id) + str(return_update_product[1])]
        return [0, 0]

    @api.model
    def _magento_product_create(self, connection, pro_id, special_values):
        """ Method to create a product on a Magento Website
        :param cr: current cursor
        :param uid: current user
        :param connection: current connection
        :param pro_id: odoo product id
        :param prodtype: magento product type
        :param prodsku: magento product sku
        :param put_product_data: product data to create
        :return:
        """

        server = xmlrpclib.Server(connection[0])

        magento_set_id = special_values.get('attribute_set_id')
        magento_sku = special_values.get('sku')
        magento_type = special_values.get('type')
        magento_product_values = special_values.get('product_data')

        newprod = [magento_type, magento_set_id, magento_sku, magento_product_values]
        try:
            pro = server.call(connection[1], 'product.create', newprod)
        except xmlrpclib.Fault, e:
            _logger.debug('Error: %s', e)
            return [0, str(pro_id) + str(e)]

        if pro:
            mapping_values = {
                'pro_name': pro_id,
                'oe_product_id': pro_id,
                'mag_product_id': pro,
                'need_sync': 'No'
            }

            _logger.debug("mapping values: %s", mapping_values)

            self.env['magento.product'].create(
                mapping_values
            )

            # Extra Commit to fix performance issues
            self._cr.commit()

            # Create Mapping on Magento
            server.call(
                connection[1],
                'odoolink.product_map',
                [
                    {
                        'mage_product_id': pro,
                        'erp_product_id': pro_id
                    }
                ]
            )

            return [1, pro]

    @api.multi
    def prodimage(self, connection, product, magento):
        """
        Product Image Creation or Update
        :param cr: cursor
        :param uid: user
        :param connection: current connection
        :param product: current product
        :param magento: magento product id (string)
        :param context:
        :return: True or False
        """
        if isinstance(magento, (int, long)):
            magento = str(magento)

        url = connection[0]
        session = connection[1]
        server = xmlrpclib.Server(url)

        if magento and magento != 0 and product.image:
            file = {'content': product.image,
                    'mime': 'image/jpeg',
                    'name': product.name}
            type = ['image', 'small_image', 'thumbnail']
            pic = {'file': file,
                   'label': product.name,
                   'position': '1',
                   'types': type,
                   'exclude': 0}
            image = [magento, pic]
            image_remove = []

            if product.magento_image_change:

                image_update = [magento, product.magento_image, pic]

                if product.magento_image:

                    image_remove = [magento, product.magento_image]

                    try:
                        result = server.call(session,
                                             'catalog_product_attribute_media.remove',
                                             image_remove)
                        if result:
                            _logger.debug('Image Removal Succesfull')
                            product.write(
                                {'magento_image': False})
                    except:
                        _logger.debug('Image Removal Error: %s', (str(image_remove)))

                try:
                    filename = server.call(session,
                                           'catalog_product_attribute_media.create',
                                           image)
                except:
                    filename = False

                _logger.debug('Product Image Create Return: %s', str(filename))

                if filename:
                    self.env['product.product'].browse(product.id).write(
                        {'magento_image': filename,
                         'magento_image_change': False})
                else:
                    _logger.debug('No filename return from Magento')
                    return False
        return True

    @api.multi
    def _export_specific_product(self, p_id, connection):

        if id:


            ctx = self._context.copy()
            if connection[2].lang:
                ctx.update({'lang': connection[2].lang})

            product = self.env['product.product'].browse(p_id)

            # Get product categories
            prod_catg = self._get_product_categories(connection, product)

            # Get product data
            get_product_data = self._get_magento_product_values([product,
                                                                 prod_catg,
                                                                 connection,
                                                                 'create'])
            sku = product.default_code or 'Ref %s' % id
            get_product_data['status'] = 2
            ##TODO: Make this configurable parameter or Map the taxes
            get_product_data['tax_class_id'] = 4 # Current Default Tax Class
            # get_product_data['barcode'] = product.ean13 or False

            if product.magento_type:
                prodtype = product.magento_type.name
            else:
                _logger.error("No magento type defined on product")
            if product.magento_attribute_set:
                attribute_set_id = product.magento_attribute_set.set_id
            else:
                _logger.error("No magento attribute set defined on product")
                return [0, 0]
            magento_values = {
                'attribute_set_id': attribute_set_id,
                'sku': sku,
                'type': prodtype,
                'product_data': get_product_data,
            }

            pro = self._magento_product_create(connection, product.id, magento_values)
            _logger.debug('Product Create Return: %s', str(pro))

            if connection[2].store_ids and pro[0] == 1:
                _logger.debug('Browse Stores')
                for store in connection[2].store_ids:
                    _logger.debug('Current Store: %s', store.id)
                    # Get Store View Product Data
                    if not store.active:
                        _logger.debug('Store inactive: %s', store.id)
                        break
                    get_store_product_data = self._get_magento_store_product_values(
                        [product, store, 'create'])
                    _logger.debug('Product Data: %s', get_store_product_data)

                    if get_store_product_data:
                        # Extra Update so don't pass the product_id
                        self._magento_update_product(
                            connection,
                            pro[1],
                            get_store_product_data,
                            store_id=store.store_id,
                        )

            if pro[0] == 1:
                # Update product stock on magento
                stock_values = self._get_magento_product_stock_values(product)
                self._magento_update_product_stock(
                    connection,
                    pro[1],
                    stock_values)

                # Update product images on magento
                if connection[2].product_create_image:
                    self.prodimage(
                        connection,
                        product,
                        pro[1]
                    )

            return pro

    @api.multi
    def export_products(self):
        """
        Export All Products
        :param cr: cursor
        :param uid: user
        :param ids: list of ids
        :param context:
        :return:
        """
        error_ids = []
        success_ids = []
        map_dic = []
        catg_dict = {}
        catg_list = []
        text = text1 = ''
        connection = self.env['magento.configure']._create_connection()
        if connection:
            server = xmlrpclib.Server(connection[0])
            map_id = self.env['magento.product'].search([])
            for map_obj in map_id:
                map_dic.append(map_obj.oe_product_id)
            erp_pro = self.env['product.product'].search([
                ('active', '=', True),
                ('id', 'not in', map_dic)])
            if not erp_pro:
                raise UserError(_("No new product(s) found."))
            for l in erp_pro:
                pro = self._export_specific_product(l.id, connection)
                if pro[0] != 0:
                    success_ids.append(l)
                else:
                    error_ids.append(pro[1])
            if success_ids:
                text = 'The Listed Product ids %s has been sucessfully Exported to Magento. \n' % success_ids
                self.env['magento.sync.history'].create({'status': 'yes',
                                                         'action_on': 'product',
                                                         'action': 'b',
                                                         'error_message': text})
            if error_ids:
                text1 = 'The Listed Product ids %s Reference(SKU) has been already exists on magento.' % error_ids
                self.env['magento.sync.history'].create({'status': 'no',
                                                         'action_on': 'product',
                                                         'action': 'b',
                                                         'error_message': text1})
            partial = self.env['message.wizard'].create({'text': text + text1})
            return {'name': _("Information"),
                    'view_mode': 'form',
                    'view_id': False,
                    'view_type': 'form',
                    'res_model': 'message.wizard',
                    'res_id': partial.id,
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                    'domain': '[]'}

    #############################################
    ##    export bulk/selected products  	   ##
    #############################################

    @api.model
    def export_bulk_product(self):
        text = ''
        text1 = text2 = ''
        fail_ids = []
        error_ids = []
        up_error_ids = []
        success_up_ids = []
        success_exp_ids = []
        get_product_data = {}

        bulk_ids = self._context.get('active_ids')
        map_obj = self.env['magento.product']
        connection = self.env['magento.configure']._create_connection()
        if connection:
            for l in bulk_ids:
                search = map_obj.search([('pro_name', '=', l)])
                if not search:
                    pro = self._export_specific_product(l, connection)
                    if pro[0] != 0:
                        success_exp_ids.append(l)
                    else:
                        error_ids.append(pro[1])
                else:
                    mapping = search[0]
                    if mapping.need_sync == 'Yes':
                        pro_update = self._update_specific_product(mapping, connection)
                        if pro_update[0] != 0:
                            success_up_ids.append(pro_update[1])
                        else:
                            up_error_ids.append(pro_update[1])
                    else:
                        fail_ids.append(l)
            if success_exp_ids:
                text = "\nThe Listed Product ids %s has been created on magento." % (success_exp_ids)
            if fail_ids:
                text += "\nSelected product ids %s are already synchronized on magento." % (fail_ids)
            if error_ids:
                text += '\nThe Listed Product ids %s Reference(SKU) has been already exists on magento.' % error_ids
            if text:
                self.env['magento.sync.history'].create({
                    'status': 'yes',
                    'action_on': 'product',
                    'action': 'b',
                    'error_message': text
                })
            if success_up_ids:
                text1 = '\nThe Listed Product ids %s has been successfully updated to Magento. \n' % success_up_ids
                self.env['magento.sync.history'].create({
                    'status': 'yes',
                    'action_on': 'product',
                    'action': 'c',
                    'error_message': text1
                })
            if up_error_ids:
                text2 = '\nThe Listed Product ids %s does not updated on magento.' % up_error_ids
                self.env['magento.sync.history'].create({
                    'status': 'no',
                    'action_on': 'product',
                    'action': 'c',
                    'error_message': text2
                })
            partial = self.env['message.wizard'].create(
                {'text': text + text1 + text2})
            return {'name': _("Information"),
                    'view_mode': 'form',
                    'view_id': False,
                    'view_type': 'form',
                    'res_model': 'message.wizard',
                    'res_id': partial.id,
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                    'domain': '[]'}

    @api.multi
    def update_Customers_button(self):
        self.update_Customers()

    @api.model
    def update_Customers(self):
        """
        Update Customers
        :param cr: cursor
        :param uid: user
        :param ids: list of (customer)ids
        :param context:
        :return:
        """
        count = 0
        text = text1 = ''
        error_ids = []

        connection = self.env['magento.configure']._create_connection()
        if connection:
            server = xmlrpclib.Server(connection[0])
            map_ids = self.env['magento.customers'].search([
                ('need_sync', '=', 'Yes')])

            if not(map_ids):
                raise UserError(_("No customer(s) has been found to be Update on Magento!!!"))
            if map_ids:
                for mapp in map_ids:
                    get_customer_data = {}
                    get_address_data = {}
                    street = []
                    if mapp.oe_customer_id:
                        oe_customers = self.env['res.partner'].browse(mapp.oe_customer_id)
                    if oe_customers:
                        oe_customer = oe_customers[0]
                        cus_id = oe_customer.id
                        mage_cus_id = mapp.mag_customer_id
                        try:
                            mage_add_id = int(mapp.mag_address_id)
                        except:
                            mage_add_id = 0
                        if oe_customer.parent_id:
                            get_address_data['company'] = oe_customer.parent_id.name

                        name = oe_customer.name.split(' ', 1)
                        if len(name) > 1:
                            get_customer_data['firstname'] = name[0]
                            get_customer_data['lastname'] = name[1]
                            get_address_data['firstname'] = name[0]
                            get_address_data['lastname'] = name[1]
                        else:
                            get_customer_data['firstname'] = name[0]
                            get_customer_data['lastname'] = name[0]
                            get_address_data['lastname'] = name[0]
                            get_address_data['firstname'] = name[0]

                        get_address_data['country_id'] = 'NL'
                        code = 'NL'
                        if oe_customer.country_id.id:
                            code = oe_customer.country_id.code
                            get_address_data['country_id'] = code

                        #housenumber and street
                        street.append(oe_customer.street_name or 'None')
                        street.append(oe_customer.street2 or 'None')
                        get_address_data['housenumber'] = oe_customer.street_number
                        get_address_data['housenumberadd'] = oe_customer.street_number
                        get_address_data['street'] = street
                        get_address_data['city'] = oe_customer.city or False
                        get_address_data['postcode'] = oe_customer.zip or False
                        get_address_data['telephone'] = oe_customer.phone or False
                        get_address_data['fax'] = oe_customer.fax or False
                        if oe_customer.vat:
                            get_address_data['vat_id'] = oe_customer.vat
                        try:
                            if mage_cus_id > 0 and oe_customer.magento_user:
                                update_data = [mage_cus_id, get_customer_data]
                                _logger.debug('Customer Update (Magento User): %s',
                                              str(update_data))
                                server.call(connection[1], 'customer.update',
                                            update_data)
                            if mage_add_id > 0 and not(oe_customer.magento_user):
                                update_data = [mage_add_id, get_address_data]
                                _logger.debug('Customer Update: %s',
                                              str(update_data))
                                server.call(connection[1],
                                            'customer_address.update',
                                            update_data)
                            count = count + 1
                            self.env['magento.customers'].browse(mapp.id).write(
                                {'need_sync': 'No'})
                            self._cr.commit()
                        except xmlrpclib.Fault, e:
                            error_ids.append(cus_id)
                if count:
                    text = '%s Customer has been sucessfully updated to Magento. \n' % count
                    self.env['magento.sync.history'].create({
                        'status': 'yes',
                        'action_on': 'customer',
                        'action': 'c',
                        'error_message': text
                    })
                if error_ids:
                    text1 = 'The Listed Customer ids %s does not updated on magento.' % error_ids
                    self.env['magento.sync.history'].create({'status': 'no',
                                                             'action_on': 'customer',
                                                             'action': 'c',
                                                             'error_message': text1})
                partial = self.env['message.wizard'].create({'text': text + text1})
                return {'name': _("Information"),
                        'view_mode': 'form',
                        'view_id': False,
                        'view_type': 'form',
                        'res_model': 'message.wizard',
                        'res_id': partial.id,
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]'}

    @api.model
    def get_mage_region_id(self, connection, region, country_code):
        """
        @return magneto region id
        """
        region_obj = self.env['magento.region']
        map_id = region_obj.search([('country_code', '=', country_code)])
        if not map_id:
            return_id = self.env['region.wizard']._sync_mage_region(connection,
                                                                    country_code)
        region_ids = region_obj.search([('name', '=', region),
                                        ('country_code', '=', country_code)])
        if region_ids:
            id = region_obj.browse(region_ids[0].id).mag_region_id
            return id
        else:
            return 0


class magento_category(models.Model):
    _name = "magento.category"
    _order = 'id desc'
    _rec_name = "cat_name"
    _description = "Magento Category"

    cat_name = fields.Many2one('product.public.category', 'Category Name')
    oe_category_id = fields.Integer('Openerp Category Id')
    mag_category_id = fields.Integer('Magento Category Id')
    need_sync = fields.Selection([('Yes', 'Yes'), ('No', 'No')],
                                 'Update Required')
    create_date = fields.Datetime('Created Date')
    write_date = fields.Datetime('Updated Date')

    _defaults = {
        'need_sync': 'No',
    }

    @api.model
    def create_category(self, data):
        """Create and update a category by any webservice like xmlrpc.
        @param data: details of category fields in list.
        """
        categ_dic = {}
        category_id = 0
        if data.get('name'):
            categ_dic['name'] = urllib.unquote_plus(data.get('name').encode('utf8'))
        if data.get('parent_id'):
            categ_dic['parent_id'] = data.get('parent_id')
        if data.get('method') == 'create':
            mage_category_id = data.get('mage_id')
            category_id = self.env['product.public.category'].create(categ_dic)
            self.create({
                'cat_name': category_id.id,
                'oe_category_id': category_id.id,
                'mag_category_id': mage_category_id
            })
            return category_id.id
        if data.get('method') == 'write':
            category_id = data.get('category_id')
            self.env['product.public.category'].browse(category_id).write(categ_dic)
            return True
        return False


class magento_customers(models.Model):
    _name = "magento.customers"
    _order = 'id desc'
    _rec_name = "cus_name"
    _description = "Magento Customers"

    cus_name = fields.Many2one('res.partner', 'Customer Name')
    oe_customer_id = fields.Integer('Openerp Customer Id')
    mag_customer_id = fields.Char('Magento Customer Id', size=50)
    mag_address_id = fields.Char('Magento Address Id', size=50)
    need_sync = fields.Selection([('Yes', 'Yes'), ('No', 'No')],
                                 'Update Required')
    create_date = fields.Datetime('Created Date')
    write_date = fields.Datetime('Updated Date')

    _defaults = {
        'need_sync': 'No',
    }


class magento_user(models.Model):
    _name = "magento.user"
    _order = "id desc"
    _description = "Magento Users"

    name = fields.Char("Magento User Name", size=64)
    email = fields.Char("Magento User Email", size=64)


class magento_region(models.Model):
    _name = "magento.region"
    _order = 'id desc'
    _description = "Magento Region"

    name = fields.Char('Region Name', size=100)
    mag_region_id = fields.Integer('Magento Region Id')
    country_code = fields.Char('Country Code', size=10)
    region_code = fields.Char('Region Code', size=10)
    create_date = fields.Datetime('Created Date')
    write_date = fields.Datetime('Updated Date')


class magento_orders(models.Model):
    _name = "magento.orders"
    _order = 'id desc'
    _rec_name = "order_ref"
    _description = "Magento Orders"

    order_ref = fields.Many2one('sale.order', 'Order Reference')
    oe_order_id = fields.Integer('Openerp order Id')
    mag_orderIncrement_Id = fields.Char('Magento order Id', size=100)
    create_date = fields.Datetime('Created Date')
    write_date = fields.Datetime('Updated Date')

    @api.model
    def create_pricelist(self, data):
        """create and search pricelist by any webservice like xmlrpc.
        @param code: currency code.
        @param context: A standard dictionary
        @return: pricelist_id
        """
        currency_ids = self.env['res.currency'].search([
            ('name', '=', data['code'])]) or [False]
        pricelist_ids = self.env['product.pricelist'].search([
            ('currency_id', '=', currency_ids[0].id)]) or [
            False]
        if not pricelist_ids:
            pricelist_dict = {'name': 'Mage_' + data['code'],
                              'active': True,
                              'type': 'sale',
                              'currency_id': currency_ids[0].id,
                             }
            pricelist_id = self.env["product.pricelist"].create(pricelist_dict)
            version_dict = {
                'name': data['code'] + ' Public Pricelist Version',
                'pricelist_id': pricelist_id.id,
                'active': True,
            }
            product_version_id = self.env['product.pricelist.version'].create(version_dict)
            price_type_id = self.env['product.price.type'].search([
                ('name', '=', 'Public Price')])
            item_dict = {'name': data['code'] + ' Public Pricelist Line',
                         'price_version_id': product_version_id.id,
                         'base': price_type_id[0].id,
                        }
            product_pricelist_item_id = self.env['product.pricelist.item'].create(item_dict)
            return pricelist_id.id
        else:
            return pricelist_ids[0].id

    @api.multi
    def _get_journal_code(self, string, sep=' '):
        tl = []
        for t in string.split(sep):
            t2 = t.title()[0]
            if t2.isalnum():
                tl.append(t2)
        code = ''.join(tl)
        code = code[0:3]
        is_exist = self.env['account.journal'].search([('code', '=', code)])
        if is_exist:
            for i in range(1, 99):
                is_exist = self.env['account.journal'].search([
                    ('code', '=', code + str(i))])
                if not is_exist:
                    return code + str(i)[-5:]
        return code

    @api.model
    def create_payment_method(self, data):
        """create Journal by any webservice like xmlrpc.
        @param name: journal name.
        @param context: A standard dictionary
        @return: payment_id
        """
        res = self.env['account.journal'].search([('type', '=', 'bank')], limit = 1)
        if not res:
            raise Exception('No Journal Found for a Bank Type..')
        else:
            res = res[0]
        credit_account_id = res.default_credit_account_id.id
        debit_account_id = res.default_debit_account_id.id
        data['default_credit_account_id'] = credit_account_id
        data['default_debit_account_id'] = debit_account_id
        data['code'] = self._get_journal_code(data.get('name'))
        payment_id = self.env['account.journal'].create(data)
        return payment_id.id

    @api.multi
    def _get_product_id(self, product_data):
        pro_dic = {}
        default_code = urllib.unquote_plus(product_data['sku'].encode('utf8'))
        ctx = self._context.copy()
        ctx.update({'active_test': False})
        product_ids = self.env['product.product'].search([
            ('default_code', '=', default_code)])
        if not product_ids:
            pro_dic['name'] = urllib.unquote_plus(product_data['name'].encode('utf8'))
            if product_data['product_type'] != 'simple':
                pro_dic['type'] = 'service'
            else:
                pro_dic['type'] = 'product'
            pro_dic['list_price'] = 0.00
            pro_dic['active'] = True
            pro_dic['default_code'] = default_code
            categ_ids = self.env['product.category'].search([
                ('name', '=', 'Shipping/Voucher')])
            if not categ_ids:
                category_id = self.env['product.category'].create({
                    'name': 'Shipping/Voucher',
                    'type': 'normal'
                })
                pro_dic['categ_id'] = category_id.id
            else:
                pro_dic['categ_id'] = categ_ids[0].id
            product_id = self.env['product.product'].create(pro_dic)
            return product_id.id
        else:
            pro_dic = {'active': True}
            product_ids.write(pro_dic)
            return product_ids[0].id

    @api.model
    def extra_order_line(self, data):
        """
        Method to create extra order lines needed for discount, shipping etc.
        :param cr:
        :param uid:
        :param data:
        :param context:
        :return: new line id
        """
        line_dic = {}

        sale_order_line = self.env['sale.order.line']

        # Get or create a new product
        product_id = self._get_product_id(data)
        amount = data.get('price_unit') or 0.0

        # Gift certificate specific
        if data.get('giftcert_code'):
            line_dic['name'] = data.get('giftcert_code')
            amount *= -1

        # Bundle Discount specific
        if data.get('bundle_code'):
            line_dic['name'] = data.get('bundle_code')
            amount *= -1

        # Coupons specific
        if data.get('coupon_code'):
            line_dic['name'] = data.get('coupon_code')

        # Shipping specific
        if data.get('shipping_description'):
            shipping_description = urllib.unquote_plus(
                data.get('shipping_description').encode('utf8')
            )
            line_dic['name'] = shipping_description

        # Discount specific
        if data.get('discount'):
            line_dic['discount'] = data.get('discount')

        # Add values to sale order line dict
        line_dic['order_id'] = data['order_id']
        line_dic['price_unit'] = amount
        line_dic['product_id'] = product_id
        line_dic['product_uom_qty'] = 1
        line_dic['product_uom'] = 1

        line_dic = self.get_order_line_tax(line_dic)

        _logger.debug("Create Extra Order Line: %s", line_dic)

        # Create the order line
        line_id = sale_order_line.create(line_dic)

        return line_id.id

    @api.model
    def create_order_line(self, data):
        """create sale order line by any webservice like xmlrpc.
        @param data: dictionary of OpenERP Order ID and line information.
        @param context: A standard dictionary
        @return: line_id
        """
        line_dic = {}
        product = self.env['product.product']
        sale_order_line = self.env['sale.order.line']
        if data.get('product_id', False):
            line_dic['product_id'] = data.get('product_id')
            line_dic['type'] = product.browse(
                data.get('product_id')
            ).route_ids

            purchase_price = product.browse(
                data.get('product_id')
            ).standard_price

            if purchase_price:
                line_dic['purchase_price'] = purchase_price

        if data.get('name', False) and data['name']:
            line_dic['name'] = urllib.unquote_plus(
                data.get('name').encode('utf8')
            )

        line_dic['product_uom_qty'] = data.get('product_uom_qty', False)
        line_dic['product_uom'] = 1
        line_dic['discount'] = data.get('discount', False)
        line_dic['order_id'] = data.get('order_id', False)
        line_dic['price_unit'] = data.get('price_unit', False)

        line_dic = self.get_order_line_tax(line_dic)

        line_id = sale_order_line.create(line_dic)
        line_id.write(line_dic)
        return line_id.id

    @api.multi
    def get_order_line_tax(self, line_dic):
        order = self.env['sale.order'].browse(line_dic['order_id'])
        product = self.env['product.product'].browse(line_dic['product_id'])

        fpos = order.fiscal_position_id or order.partner_id.property_account_position_id
        taxes = product.taxes_id
        taxes = (fpos.map_tax(taxes, product, order.partner_shipping_id) if fpos else taxes)
        line_dic['tax_id'] = [(6, 0, [taxes.ids])]

        if order.pricelist_id and order.partner_id:
            line_dic['price_unit'] = self.env['account.tax']._fix_tax_included_price(line_dic['price_unit'], product.taxes_id, taxes)

        return line_dic

    @api.depends('order_id')
    def sales_reorder(self):
        """Create a new Copy of Quotation order by any webservice like xmlrpc.
        @param order_id: OpenERP Order ID.
        @param context: A standard dictionary
        @return: newly created order id.
        """
        reorder_id = self.env['sale.order'].copy_quotation(
            [order_id]
        )['res_id']

        if reorder_id:
            self.env['sale.order'].browse(reorder_id).action_confirm(
            )

        return reorder_id.id

    @api.depends('order_id')
    def order_cancel(self):
        """Cancel an order by any webservice like xmlrpc.
        @param order_id: OpenERP Order ID.
        @param context: A standard dictionary
        @return: True
        """
        order_name = self.env['sale.order'].name_get(
            [order_id]
        )

        pick_id = self.env['stock.picking'].search(
            [
                ('origin', '=', order_name[0][1])
            ]
        )

        if pick_id:
            pick_cancel = self.env['stock.picking'].action_cancel(pick_id.id)
        order_cancel = self.env['sale.order'].action_cancel([order_id])

        return True

    @api.model
    def _get_parent_dic(self, values, type, companyname):
        _logger.debug('Customer Parent (Request): %s', str(values))
        new_values = values.copy()
        new_values['name'] = companyname and urllib.unquote_plus(companyname.encode('utf8'))
        new_values['name'] = new_values['name'].strip()
        new_values['customer'] = True
        new_values['is_company'] = True

        if type == 'delivery':
            new_values = self._remove_address_dic(new_values,
                                                  onlyaddress=False)

        _logger.debug('Customer Parent (Added Values): %s', str(values))
        return new_values

    @api.multi
    def _remove_address_dic(self, values, onlyaddress=False):
        new_values = values

        if new_values.get('street', False):
            del new_values['street']
        if new_values.get('street2', False):
            del new_values['street2']
        if new_values.get('city', False):
            del new_values['city']
        if new_values.get('zip', False):
            del new_values['zip']
        if new_values.get('country_id', False):
            del new_values['country_id']
        if new_values.get('state_id', False):
            del new_values['state_id']
        if not(onlyaddress):
            if new_values.get('phone', False):
                del new_values['phone']
            if new_values.get('fax', False):
                del new_values['fax']
            if new_values.get('email', False):
                del new_values['email']
            if new_values.get('vat', False):
                del new_values['vat']

        return new_values

    @api.model
    def create_customer(self, data):
        """Create a customer by any webservice like xmlrpc.
        @param data: details of customer fields in list.
        @param context: A standard dictionary
        @return: Openerp Customer id
        """
        cus_dic = {}
        _logger.debug('Create Customer (Initial Data): %s', str(data))
        # Get correct language and section from store
        if data.get('store_id'):
            magstore_ids = self.env['magento.store'].search(
                [('store_id', '=', data.get('store_id'))])
            if magstore_ids:
                magstore_id = magstore_ids[0].id  # Should always be one result
                magstore = self.env['magento.store'].browse(magstore_id)
                if magstore.lang:
                    cus_dic['lang'] = magstore.lang
                if magstore.sales_team_id:
                    cus_dic['team_id'] = magstore.sales_team_id.id

        # Get the correct language and section from magento user
        elif data.get('magento_user_id'):
            partner_obj = self.env['res.partner'].browse(data.get('magento_user_id'))
            if partner_obj:
                if partner_obj.lang:
                    cus_dic['lang'] = partner_obj.lang
                if partner_obj.team_id:
                    cus_dic['team_id'] = partner_obj.team_id.id

        if data.get('country_code'):
            country_ids = self.env['res.country'].search([('code', '=', data.get('country_code'))])
            cus_dic['country_id'] = country_ids[0].id

        cus_dic['customer'] = True
        cus_dic['name'] = data.get('name', False) and urllib.unquote_plus(data.get('name').encode('utf8'))
        cus_dic['name'] = cus_dic['name'].strip()
        cus_dic['email'] = data.get('email', False) and urllib.unquote_plus(data.get('email').encode('utf8'))
        cus_dic['street_name'] = data.get('street', False) and urllib.unquote_plus(data.get('street').encode('utf8'))
        cus_dic['street_number'] = data.get('housenumber', False) and urllib.unquote_plus(data.get('housenumber').encode('utf8'))
        if data.get('housenumberadd'):
            cus_dic['street_number_ext'] = data.get('housenumberadd', False) and urllib.unquote_plus(data.get('housenumberadd').encode('utf8'))
        cus_dic['street2'] = data.get('street2', False) and urllib.unquote_plus(data.get('street2').encode('utf8'))
        cus_dic['city'] = data.get('city', False) and urllib.unquote_plus(data.get('city').encode('utf8'))
        cus_dic['type'] = data.get('type', False)
        cus_dic['zip'] = data.get('zip', False)
        cus_dic['phone'] = data.get('phone', False)
        cus_dic['fax'] = data.get('fax', False)
        if cus_dic['type'] == 'default':
            cus_dic['type'] = 'contact'

        not_user = True
        if data.get('is_user'):
            # This is a magento user not a customer
            customer_id = self.env['res.partner'].search(['|',('id','=',data.get('magento_user_id',0)),('email', '=', cus_dic['email'])], limit=1)
            if customer_id:
                return customer_id.id
            else:
                cus_dic = {'name': cus_dic['name'], 'email': cus_dic['email']}
        if not_user:
            # This is a magento adress and odoo client,
            # if tag then create a parent_id, is_company=true
            if data.get('vat_id'):
                cus_dic['vat'] = data.get('vat_id')
            customer_id = self.env['res.partner'].search(['|',('id','=',data.get('magento_user_id',0)),('email', '=', cus_dic['email'])], limit=1)
            if data.get('method', '') == 'create' and not customer_id:
                _logger.debug('Create Customer (Init Dic): %s', str(cus_dic))
                # check if company
                if data.get('company', False):

                    parent_dic = self._get_parent_dic(
                        cus_dic.copy(),
                        cus_dic.get('type', 'invoice'),
                        data.get('company', 'No Company'),
                    )
                    # search if company is already available in system
                    parent_id = self.env['res.partner'].search(
                        [('name', '=', parent_dic['name']),
                         ('is_company', '=', True)]
                    )

                    if not(parent_id):
                        try:
                            cus_dic['is_company'] = True
                            parent_id = self.env['res.partner'].create(parent_dic)
                        except:
                            if parent_dic.get('vat'):
                                _logger.debug('Invalid VATID: %s',
                                              (parent_dic['vat']))
                                del parent_dic['vat']
                                parent_id = self.env['res.partner'].create(parent_dic)
                            else:
                                _logger.debug('Error creating customer/parent: %s',
                                              str(parent_dic))

                    else:
                        # if company found get id
                        try:
                            parent_id = parent_id[0]
                            parent_id.write(parent_dic)
                        except:
                            try:
                                _logger.debug('Invalid VATID: %s',
                                              (parent_dic['vat']))
                                del parent_dic['vat']
                                parent_id.write(parent_dic)
                            except:
                                _logger.debug('Customer Parent_ID Not available')

                    cus_dic['parent_id'] = parent_id.id
                    cus_dic['customer'] = True
                    cus_dic['is_company'] = False

                    # if parent address is used remove street values

                _logger.debug('Create Customer')
                cus_dic['name'] = data.get('name', False) and urllib.unquote_plus(data.get('name').encode('utf8'))
                cus_dic['name'] = cus_dic['name'].strip()

                customer_id = self.env['res.partner'].create(cus_dic)
                return customer_id.id

            else:
                if data.get('company', False):
                    # get the parent_dic
                    parent_dic = self._get_parent_dic(cus_dic.copy(),
                                                      cus_dic.get('type', 'invoice'),
                                                      data.get('company', 'No Company'))
                    customers = [customer_id]
                    for customer in customers:
                        if not(customer.parent_id):
                            # if existing customer exisits get id
                            parent_id = self.env['res.partner'].create(parent_dic)

                            # Lets see how this functions

                        else:
                            self.env['res.partner'].browse(customer.parent_id.id).write(parent_dic)
                            parent_id = customer.parent_id
                            # if not a delivery order use parent address

                    cus_dic['parent_id'] = parent_id.id
                    if cus_dic['type'] != 'delivery':
                        cus_dic['customer'] = False
                    else:
                        cus_dic['customer'] = True
                    cus_dic['is_company'] = False

                    # if parent address is used remove street values

                cus_dic['name'] = data.get('name', False) and urllib.unquote_plus(data.get('name').encode('utf8'))
                cus_dic['name'] = cus_dic['name'].strip()
                customer_id.write(cus_dic)
                return customer_id.id
        return False

    @api.model
    def create_order_invoice(self, data):
        """
        Order Create from Magento
        :param cr: cursor
        :param uid: user
        :param data: data from magento
        :param context:
        :return:
        """

        order_obj = self.env['sale.order']
        _logger.debug('Create Invoice Order (data): %s', str(data))

        if data.get('order_id'):
            for order in self.env['sale.order'].browse([data.get('order_id')]):

                if order.state in ('draft', 'sent', 'cancel'):
                    if order.state in ('cancel'):
                        _logger.debug('Reactivate Order: %s', str(order.id))
                        order.action_draft()

                    _logger.debug('Confirm order when state quotation and '
                                  'create invoice called: %s', str(order.id))
                    order.action_confirm()

                search_invoice_ids = self.env['account.invoice'].search([
                    ('origin', 'ilike', order.name)])
                if search_invoice_ids:
                    _logger.debug('List Found Invoice IDS: %s', str(search_invoice_ids))
                    invoice_id = search_invoice_ids[0].id
                    _logger.debug('Found Invoice ID: %s', str(invoice_id))
                else:
                    _logger.debug('Create invoice from order: %s', str(order.id))
                    inv_ids = order.action_invoice_create()

                    invoice_id = inv_ids[0]
                    _logger.debug('Created invoice: %s', str(invoice_id))

                if data.get('date'):
                    self.env['account.invoice'].browse(invoice_id).write({
                        'date_invoice': data.get('date'),
                        'date_due': data.get('date'),
                        'magento_invoice': data['mage_inv_number']
                    })

                self.env['account.invoice'].browse([invoice_id]).action_invoice_open()

        return invoice_id

    # code for Payment an order......
    @api.multi
    def _get_journal_id(self):
        if self._context.get('invoice_id', False):
            currency_id = self.env['account.invoice'].browse(self._context['invoice_id']).currency_id.id
            journal_id = self.env['account.journal'].search(
                [('currency', '=', currency_id)],
                limit=1)
            return journal_id and journal_id[0].id or False
        res = self.env['account.journal'].search([('type', '=', 'bank')],
                                                 limit=1)
        return res and res[0].id or False

    @api.model
    def _get_tax_id(self, journal_id):
        journal = self.env['account.journal'].browse(journal_id)
        account_id = journal.default_credit_account_id or journal.default_debit_account_id
        if account_id and account_id.tax_ids:
            tax_id = account_id.tax_ids[0].id
            return tax_id
        return False

    @api.model
    def _get_currency_id(self, journal_id):
        journal = self.env['account.journal'].browse(journal_id)
        if journal.currency:
            return journal.currency.id
        return self.env['res.users'].browse().company_id.currency_id.id

    @api.model
    def sales_order_payment(self, payment):
        """
        @param payment: List of invoice_id, reference, partner_id ,journal_id and amount
        @param context: A standard dictionary
        @return: True
        """
        _logger.debug('Register Payment: %s', (payment,))

        if payment.get('partner_id'):
            partner_id = payment.get('partner_id')
            partner_obj = self.env['res.partner'].browse(partner_id)
            for partner in partner_obj:
                partner_id = partner.parent_id and partner.parent_id.id or partner.id

        journal_id = payment.get('journal_id', False)
        if not journal_id:
            journal_id = self._get_journal_id()

        if payment.get('amount'):
            amount = payment.get('amount', 0.0)
            try:
                amount = float(amount)
            except:
                _logger.debug('Wrong amount from magento')
                amount = 0.0
        else:
            _logger.debug('No amount from magento')
            amount = 0.0
        _logger.debug('Payment Amount: %s', (str(amount)))
        invoice_obj = self.env['account.invoice'].browse(payment.get('invoice_id'))

        journal = self.env['account.journal'].browse(journal_id)
        invoice_obj.pay_and_reconcile(journal, pay_amount=amount)
        return True

    # code for shipping an order......

    @api.model
    def order_shipped(self, data):
        order_obj = self.env['sale.order']
        #self._context['stock_from'] = 'magento'
        active_id = self.env['magento.configure'].search([
            ('active', '=', True)])
        if active_id:
            self.env['magento.configure'].browse(active_id[0].id).write(
                {'active': False})

        for order in self.env['sale.order'].browse(data.get('order_id')):
            if order.state in ('draft', 'sent'):
                _logger.debug('Confirm order when state quotation and '
                              'shipped called: %s', str(order.id))
                order.action_confirm()

            pick_ids = self.env['stock.picking'].search([
                ('sale_id', '=', order.id)])

            for picking in self.env['stock.picking'].browse(pick_ids.id):
                picking.do_transfer(picking.id)

        if active_id:
            self.env['magento.configure'].browse(active_id[0].id).write(
                {'active': True})

            return True
        else:
            return False

    # code for update an inventry of a product......

    @api.model
    def update_quantity(self, data):
        """ Changes the Product Quantity by making a Physical Inventory.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param data: List of product_id and new_quantity
        @param context: A standard dictionary
        @return: True
        """

        rec_id = data.get('product_id')
        #self._context['stock_from'] = 'magento'
        assert rec_id, _('Active ID is not set in Context')

        mage_qty = data.get('new_quantity')

        location_ids = self.env['stock.warehouse'].search([])
        location_id = location_ids[0].lot_stock_id.id

        quantity_wiz = self.env['stock.change.product.qty']

        inv_data = {
            'new_quantity': mage_qty,
            'location_id': location_id,
            'product_id': rec_id,
        }

        quantity_wiz_id = quantity_wiz.create(inv_data)
        if quantity_wiz_id:
            qw_return = quantity_wiz_id.change_product_qty(
            )
        return True

    @api.model
    def release_mage_order_from_hold(self, increment_id, connection):
        server = xmlrpclib.Server(connection[0])
        try:
            order_info = server.call(connection[1], 'order.info',
                                     [increment_id])
            if order_info['state'] == 'holded':
                server.call(connection[1], 'order.unhold', [increment_id])
            return True
        except Exception, e:
            return False

    @api.model
    def _get_mage_order_state(self, increment_id, connection):
        server = xmlrpclib.Server(connection[0])
        try:
            order_info = server.call(connection[1], 'order.info',
                                     [increment_id])
            return order_info.get('status')
        except Exception, e:
            return False

    @api.model
    def check_order_state(self):
        """ Checks the current state of the order in magento and acts accordingly
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of magento orders
        @param context: A standard dictionary
        @return: True
        """

        cr = openerp.registry(self._cr.dbname).cursor()

        order_obj = self.env['sale.order']
        morder_obj = self.env['magento.orders']

        if self._ids:
            orders = self._ids
        else:
            orders = order_obj.search(
                [
                    ('magento_order', '!=', False),
                    ('magento_status', 'not in', ['closed', 'complete'])
                ]
            )

        _logger.debug('Orders with Checking state: %s', str(orders))

        connection = self.env['magento.configure']._create_connection()

        if orders and connection:

            for order in orders:
                morders = morder_obj.search(
                    [
                        ('oe_order_id', '=', order.id)
                    ]
                )
                if morders:
                    _logger.debug('Magento Order(s): %s', str(morders))
                    for morder in morder_obj.browse(morders.id):
                        magento_state = self._get_mage_order_state(
                            morder.mag_orderIncrement_Id,
                            connection
                        ) or 'pending'
                        _logger.debug('Magento Order state: %s', magento_state)
                        if order.state in ('cancel') and magento_state in('processing'):
                            _logger.debug('Reactivate Order: %s',
                                          str(order.id))
                            order_obj.button_draft(
                                [order.id]
                            )
                        if order.state in ('draft', 'sent') \
                                and magento_state == 'processing':
                            _logger.debug('Confirm order: %s', str(order.id))
                            order.action_confirm()
                        if magento_state and order.magento_status != magento_state:
                            _logger.debug('Write new order state to: %s',
                                          str(order.id))
                            order_obj.browse(order.id).write({
                                'magento_status': magento_state
                            })
                self._cr.commit()

        return True


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def mage_invoice_trigger(self):
        sale_obj = self.env['sale.order']
        for inv_id in self._ids:
            invoices = self.read(inv_id, ['origin', 'state'])
            if invoices['origin']:
                sale_ids = sale_obj.search([('name', '=', invoices['origin'])])
#   manual_magento_invoice method is used to create an invoice on magento end
                if sale_ids:
                    config_id = self.env['magento.configure'].search([
                        ('active', '=', True),
                        ('auto_invoice', '=', True)])
                    if len(config_id.id) > 0:
                        mage_invoice = self.manual_magento_invoice(sale_ids.id)
                        if mage_invoice:
                            return True
        return True

    @api.model
    def manual_magento_invoice(self):
        text = ''
        status = 'no'
        mage_invoice = False

        connection = self.env['magento.configure']._create_connection()
        if connection:
                server = xmlrpclib.Server(connection[0])

                map_id = self.env['magento.orders'].search([('oe_order_id',
                                                             'in',
                                                             self._ids)])
                if map_id:
                    map_obj = map_id[0].id
                    increment_id = map_obj.mag_orderIncrement_Id
                    self.env['magento.orders'].release_mage_order_from_hold(
                        increment_id, connection)

                    try:
                        invoice_array = [increment_id, 0,
                                         'Invoiced From OpenERP',
                                         False]
                        mage_invoice = server.call(connection[1],
                                                   'sales_order_invoice.create',
                                                   invoice_array)
                        text = 'Invoice of order %s has been sucessfully updated on magento.' % map_obj.order_ref.name
                        status = 'yes'
                    except Exception, e:
                        if e.faultCode == 103:
                            text = 'Order %s invoice cannot be done on magento, Because Magento order %s does not exist on magento.' % (
                                map_obj.order_ref.name, increment_id)
                        else:
                            text = 'Invoice of order %s has been already updated on magento.' % map_obj.order_ref.name
                            status = 'yes'
                else:
                    text = 'Order invoice cannot be done from magento, Cause order id %s is created from openerp.' % self._ids
        self._cr.commit()
        self.env['magento.sync.history'].create({
            'status': status,
            'action_on': 'order',
            'action': 'b',
            'error_message': text
        })
        return mage_invoice


class magento_sync_history(models.Model):
    _name = "magento.sync.history"
    _order = 'id desc'
    _description = "Magento Synchronization History"

    status = fields.Selection((('yes', 'Successfull'),
                               ('no', 'Un-Successfull')),
                              'Status')
    action_on = fields.Selection((('product', 'Product'),
                                  ('category', 'Category'),
                                  ('customer', 'Customer'),
                                  ('order', 'Order')),
                                 'Action On')
    action = fields.Selection((('a', 'Import'),
                               ('b', 'Export'),
                               ('c', 'Update')),
                              'Action')
    create_date = fields.Datetime('Created Date')
    error_message = fields.Text('Summary')


class product_public_category(models.Model):
    _inherit = 'product.public.category'

    @api.multi
    def write(self, vals):
        map_obj = self.env['magento.category']
        if type(self._ids) == list:
            for id in self._ids:
                map_ids = map_obj.search([('oe_category_id', '=', id)])
                if map_ids:
                    map_ids.write( {'need_sync': 'Yes'})
        return super(product_public_category, self).write(vals)


class res_partner(models.Model):
    _inherit = 'res.partner'

    magento_user = fields.Boolean('Magento User')

    @api.multi
    def partners_sync(self):
        ids = list(self._ids)
        map_obj = self.env['magento.customers']
        for partner in self:
            if partner.child_ids:
                for child in partner.child_ids:
                    ids.append(child.id)
        if type(ids) == list:
            map_ids = map_obj.search([('oe_customer_id', 'in', ids)])
            if map_ids:
                map_ids.write({'need_sync': 'Yes'})

    @api.multi
    def write(self, vals):
        return_value = super(res_partner, self).write(vals)
        self.partners_sync()
        return return_value
