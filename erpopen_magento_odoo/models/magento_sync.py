# -*- coding: utf-8 -*-

import base64
import random
import logging
import threading
import sys, os

import datetime
import requests
import string

import thread
from odoo import fields, models, api, SUPERUSER_ID
import xmlrpclib

# Importazione/Esportazione Dati
from odoo import sql_db
from odoo.api import Environment
from odoo.osv import osv
from enum import Enum

LOGLEVEL = Enum('LOGLEVEL', 'info warning error')

import sys

reload(sys)
sys.setdefaultencoding("utf8")


class magento_sync(models.Model):
    _name = 'magento.sync'

    magento_web_shop_ids = fields.Many2one('magento.settings', string="Webshop")
    store_ids = fields.Many2one('magento.store')

    # -- cron methods that can be called from the front end or internally --

    def attribute_magento(self):
        socket, session = self.connection()
        attributes_set = socket.call(session, "catalog_product_attribute_set.list")
        attribute_obj = self.env['product.attribute']

        for attribute_set in attributes_set:
            attributes_set_exist = self.env['magento.attribute.set'].search(
                [('magento_id', '=', int(attribute_set['set_id']))])
            vals_set = {'magento_id': attribute_set['set_id'], 'name': attribute_set['name']}
            if not attributes_set_exist:
                self.env['magento.attribute.set'].create(vals_set)
            else:
                attributes_set_exist.write(vals_set)
            attributes = socket.call(session, "catalog_product_attribute.list",
                                     [int(attribute_set['set_id'])])
            for attribute in attributes:
                exist = attribute_obj.search([('magento_id', '=', attribute['attribute_id'])])
                if 'attribute_id' in attribute and attribute['code'] != 'allow_open_amount' and \
                                attribute['code'] != 'giftcard_type':
                    attribute_values = False
                    try:
                        attribute_values = socket.call(session, 'product_attribute.info',
                                                       [str(attribute['attribute_id'])])
                    except int:
                        print("error")
                    if attribute_values:
                        vals = {}
                        if 'code' in attribute:
                            vals['name'] = attribute['code']
                        if 'attribute_id' in attribute:
                            vals['magento_id'] = attribute['attribute_id']
                        if 'type' in attribute:
                            if attribute['type'] == 'select' or attribute['type'] == 'color':
                                vals['type'] = attribute['type']
                            else:
                                vals['type'] = 'radio'
                        vals['magento_default_value'] = attribute_values['default_value']
                        vals['magento_is_unique'] = attribute_values['is_unique']
                        vals['magento_is_required'] = attribute_values['is_required']
                        vals['magento_is_configurable'] = attribute_values['is_configurable']
                        vals['magento_is_searchable'] = attribute_values['is_searchable']
                        vals['magento_is_visible_in_advanced_search'] = attribute_values[
                            'is_visible_in_advanced_search']
                        vals['magento_is_comparable'] = attribute_values['is_comparable']
                        vals['magento_is_used_for_promo_rules'] = attribute_values[
                            'is_used_for_promo_rules']
                        vals['magento_is_visible_on_front'] = attribute_values[
                            'is_visible_on_front']
                        vals['magento_used_in_product_listing'] = attribute_values[
                            'used_in_product_listing']
                        set_id = self.env['magento.attribute.set'].search(
                            [('magento_id', '=', int(attribute_set['set_id']))])
                        if set_id:
                            vals['attribute_set_ids'] = [(4, int(set_id.id))]
                        if not exist:
                            attribute_obj.create(vals)
                            print("Created Attribute")
                        else:
                            exist.write(vals)
                            print("Changed Attribute")

                        attribute_option_obj = self.env['product.attribute.value']
                        options = socket.call(session, "catalog_product_attribute.options",
                                              [str(attribute['attribute_id'])])

                        for option in options:
                            if 'value' in option:
                                if option['value'] != '' and self.RepresentsInt(option['value']):
                                    exist = attribute_option_obj.search(
                                        [('name', '=', option['label'])])
                                    id_attribute = attribute_obj.search(
                                        [('magento_id', '=', attribute['attribute_id'])])

                                    vals = {}
                                    if id_attribute:
                                        vals['attribute_id'] = int(id_attribute.id)
                                    if 'label' in option:
                                        vals['name'] = option['label']
                                    if 'value' in option:
                                        vals['magento_id'] = int(option['value'])

                                    if not exist:
                                        attribute_option_obj.create(vals)
                                    else:
                                        exist.write(vals)

    def category_magento(self):
        socket, session = self.connection()
        categories = socket.call(session, "catalog_category.tree", [])
        self.recursive_category(categories)
        return True

    def customer_group_magento(self):
        socket, session = self.connection()
        groups = socket.call(session, "customer_group.list")
        vals = {}
        for group in groups:
            exist = self.env['magento.customers.group'].search(
                [('magento_group_id', '=', int(group['customer_group_id']))])
            if 'customer_group_id' in group:
                vals['magento_group_id'] = int(group['customer_group_id'])
            if 'customer_group_code' in group:
                vals['magento_group_code'] = group['customer_group_code']
                vals['name'] = group['customer_group_code']
            if not exist:
                self.env['magento.customers.group'].create(vals)
            else:
                exist.write(vals)

    def customer_magento(self):
        socket, session = self.connection()
        customer_list = socket.call(session, "customer.list")

        for customer in customer_list:
            self.create_customer(customer, session, socket)

    def invoice_magento(self):
        socket, session = self.connection()
        magento_settings = self.magento_web_shop_ids

        thread_blocks = []
        current_year = datetime.datetime.today().year
        start_year = 2000
        big_list = []
        n = 0

        while start_year <= current_year:
            filters = {'created_at':
                {
                    'from': str(start_year) + '-01-01 00:00:00',
                    'to': str(start_year + 1) + '-12-31 23:59:00'
                },
            }
            if magento_settings.magento_sale_order_from and magento_settings.magento_sale_order_to:
                filters = {'created_at':
                    {
                        'from': magento_settings.magento_sale_order_from,
                        'to': magento_settings.magento_sale_order_to
                    },
                }
                start_year = current_year + 1

            start_year += 2
            thread_blocks.append(filters)

        for filter in thread_blocks:
            invoice_list = socket.call(session, "sales_order_invoice.list", [filter])
            big_list.extend(invoice_list)
            n += 1

        split_list = self.split_list(big_list, 1)

        for list in split_list:
            socket, session = self.connection()
            if len(list) > 0:
                t = threading.Thread(target=self.process_invoice_list,
                                     args=(list, magento_settings, socket, session,))
                t.start()

    def product_type_magento(self):
        socket, session = self.connection()
        types = socket.call(session, "catalog_product_type.list")
        for type in types:
            exist = self.env['magento.product.type'].search([('type', '=', type['type'])])
            vals = {}
            if 'type' in type:
                vals['type'] = type['type']
                vals['name'] = type['type']
            if 'label' in type:
                vals['label'] = type['label']
            if not exist:
                self.env['magento.product.type'].create(vals)
            else:
                exist.write(vals)

    def store_magento(self):
        socket, session = self.connection()
        stores = socket.call(session, "store.list")
        for store in stores:
            exist = self.env['magento.store'].search([('magento_id', '=', int(store['store_id']))])
            vals = {}
            if 'code' in store:
                vals['code'] = store['code']
            if 'website_id' in store:
                vals['website_id'] = store['website_id']
            if 'group_id' in store:
                vals['group_id'] = store['group_id']
            if 'name' in store:
                vals['name'] = store['name']
            if 'sort_order' in store:
                vals['sort_order'] = store['sort_order']
            if 'is_active' in store:
                vals['is_active'] = store['is_active']
            vals['magento_id'] = store['store_id']
            vals['store_id'] = store['store_id']

            if not exist:
                self.env['magento.store'].create(vals)
            else:
                exist.write(vals)

    def sale_order_magento(self):
        magento_settings = self.magento_web_shop_ids
        thread_blocks = []
        current_year = datetime.datetime.today().year
        start_year = 2000
        big_list = []
        n = 0

        while start_year <= current_year:
            filters = {'updated_at':
                {
                    'from': str(start_year) + '-01-01 00:00:00',
                    'to': str(start_year + 1) + '-12-31 23:59:00'
                },
            }
            if (
                        magento_settings.magento_sale_order_from and magento_settings.magento_sale_order_to):
                filters = {'created_at':
                    {
                        'from': magento_settings.magento_sale_order_from,
                        'to': magento_settings.magento_sale_order_to
                    },
                }
                start_year = current_year + 1
            if magento_settings.magento_sale_order_status:
                filters['status'] = str(magento_settings.magento_sale_order_status)
            start_year += 2
            thread_blocks.append(filters)

        for filter in thread_blocks:
            socket, session = self.connection()
            sale_order_list = socket.call(session, "sales_order.list", [filter])
            big_list.extend(sale_order_list)
            n += 1
        self.log(LOGLEVEL.info, 'Sale order import',
                 'Found ' + str(len(big_list)) + ' sale orders to create/update')

        if len(big_list) >= 400:
            split_list = self.split_list(big_list, 4)
        else:
            split_list = []
            split_list.append(big_list)

        for list in split_list:
            socket, session = self.connection()
            if len(list) > 0:
                t = threading.Thread(target=self.process_sale_order,
                                     args=(list, magento_settings,))
                t.start()

    def product_magento(self):
        self.log(LOGLEVEL.info, 'Import', "product_magento")
        magento_settings = self.magento_web_shop_ids
        thread_blocks = []
        big_list = []
        n = 0
        alphabet = '0123456789abcdeghijklmnopqrstuvwxyzABCDEGHIJKLMNOPQRSTUVWXYZ'[::-1]

        for l in alphabet:
            filters = {
                'sku': {'like': l + "%"}
            }
            thread_blocks.append(filters)

        filters = {'updated_at':
            {
                'from': magento_settings.magento_sale_order_from,
                'to': magento_settings.magento_sale_order_to
            },
        }
        socket, session = self.connection()
        products_list = socket.call(session, "catalog_product.list", [filters])
        big_list.extend(products_list)
        n += 1
        if len(big_list) > 100:
            split_list = self.split_list(big_list, 20)
        else:
            split_list = [big_list]

        len_list = len(big_list)
        for list in split_list:
            socket, session = self.connection()
            if len(list) > 0:
                t = threading.Thread(target=self.total_product_import,
                                     args=(
                                         list, magento_settings, socket, session,
                                         len_list))
                t.start()
                len_list -= len(list)

    def new_product_magento(self):
        self.log(LOGLEVEL.info, 'Import', "new_product_magento")
        magento_settings = self.magento_web_shop_ids

        thread_blocks = []
        big_list = []
        n = 0
        alphabet = '0123456789abcdeghijklmnopqrstuvwxyzABCDEGHIJKLMNOPQRSTUVWXYZ'[::-1]

        for l in alphabet:
            filters = {
                'sku': {'like': l + "%"}
            }
            thread_blocks.append(filters)

        filters = {'updated_at':
            {
                'from': magento_settings.magento_sale_order_from,
                'to': magento_settings.magento_sale_order_to
            },
        }
        socket, session = self.connection()
        products_list = socket.call(session, "catalog_product.list", [filters])
        big_list.extend(products_list)
        n += 1
        if len(big_list) > 100:
            split_list = self.split_list(big_list, 20)
        else:
            split_list = [big_list]

        len_list = len(big_list)
        for list in split_list:
            socket, session = self.connection()
            if len(list) > 0:
                t = threading.Thread(target=self.total_product_import,
                                     args=(list, magento_settings, socket, session, len_list, True))
                t.start()
                len_list -= len(list)

    @staticmethod
    def split_list(list, n):
        avg = len(list) / float(n)
        out = []
        last = 0.0

        while last < len(list):
            out.append(list[int(last):int(last + avg)])
            last += avg

        return out

    #  -- CRON functions --

    def cron_attribute_magento(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        self.attribute_magento()

    def cron_attribute_magento_incremental(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        self.attribute_magento()  # for consistency

    def cron_category_magento(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        return self.category_magento()

    def cron_category_magento_incremental(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        return self.category_magento()  # for consistency

    def cron_customer_magento(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        return self.customer_magento()

    def cron_customer_magento_incremental(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        self.log(LOGLEVEL.info, 'CRON', "started cron incremental customer")
        socket, session = self.connection()
        magento_settings = self.magento_web_shop_ids
        filters = get_incremental_filter(magento_settings, 'customers')
        customer_list = socket.call(session, "customer.list", [filters])

        for customer in customer_list:
            self.create_customer(customer, session, socket)
        self.log(LOGLEVEL.info, 'CRON', "finished cron incremental customer")

    def cron_product_magento(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        self.product_magento()

    def cron_product_magento_incremental(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        self.log(LOGLEVEL.info, 'CRON', "started cron incremental products")
        magento_settings = self.magento_web_shop_ids
        filters = get_incremental_filter(magento_settings, 'products')
        socket, session = self.connection()
        products_list = socket.call(session, "catalog_product.list", [filters])

        if len(products_list) > 100:
            split_list = self.split_list(products_list, 50)
        else:
            split_list = [products_list]

        for list in split_list:
            socket, session = self.connection()
            if len(list) > 0:
                t = threading.Thread(target=self.total_product_import,
                                     args=(
                                         list, magento_settings, socket, session,
                                         len(products_list)))
                t.start()

    def cron_sale_order_magento(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        self.sale_order_magento()

    def cron_sale_order_magento_incremental(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        magento_settings = self.magento_web_shop_ids
        big_list = []
        filters = get_incremental_filter(magento_settings, 'sales_orders')
        self.log(LOGLEVEL.info, 'CRON',
                 'started cron incremental sale orders with filters with filters: ' + str(filters))
        socket, session = self.connection()
        sale_order_list = socket.call(session, "sales_order.list", [filters])
        big_list.extend(sale_order_list)
        if len(big_list) >= 400:
            split_list = self.split_list(big_list, 4)
        else:
            split_list = []
            split_list.append(big_list)

        if len(split_list) == 1 and len(big_list) == 0:
            self.log(LOGLEVEL.info, 'CRON',
                     'Ended cron incremental: 0 sale orders to create/update')
        else:
            self.log(LOGLEVEL.info, 'CRON',
                     'Found ' + str(len(big_list)) + ' sale orders to create/update')
        for list in split_list:
            self.process_simple_order(list)
        print "done"

    def cron_stock_magento(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        self.stock_magento()

    def cron_stock_magento_incremental(self, settings_id=1):
        self = self.env['magento.sync'].search([("magento_web_shop_ids", "=", settings_id)])
        self.stock_magento()  # for consistency

    # -- Export functions --

    def export_product(self):
        magento_settings = self.magento_web_shop_ids

        if magento_settings and magento_settings.enable_syncing_to_magento:
            socket, session = self.connection()
            product_ids = self.env['product.product'].search([('magento_id', '=', False)])
            for product in product_ids:
                print(product.default_code)
                parameter = []
                vals = {}
                parameter.append(str(product.magento_type.type))
                parameter.append(str(product.magento_set.magento_id))
                if product.default_code:
                    parameter.append(str(product.default_code))
                else:
                    parameter.append(str(self.random(5)))
                if product.magento_status:
                    vals['status'] = str('1')
                else:
                    vals['status'] = str('2')
                vals['visibility'] = str(product.magento_visibility)
                if product.magento_special_price:
                    vals['special_price'] = product['magento_special_price']
                if product.magento_special_from_date:
                    vals['special_from_date'] = str(product.magento_special_from_date)
                if product.magento_special_to_date:
                    vals['special_to_date'] = str(product.magento_special_to_date)
                if product.magento_meta_title:
                    vals['meta_title'] = str(product.magento_meta_title)
                if product.magento_meta_keyword:
                    vals['meta_keyword'] = str(product.magento_meta_keyword)
                if product.magento_meta_description:
                    vals['meta_description'] = str(product.magento_meta_description)
                if product.magento_custom_design:
                    vals['custom_design'] = str(product.magento_custom_design)
                if product.name:
                    vals['name'] = str(product.name)
                if product.list_price:
                    vals['price'] = str(product.list_price)
                if product.description_sale:
                    vals['description'] = str(product.description_sale)

                category_ids = []
                for category in product.magento_category_ids:
                    if category.magento_id:
                        category_ids.append(str(category.magento_id))
                if len(category_ids) > 0:
                    vals['category_ids'] = category_ids
                parameter.append(vals)
                parameter.append('1')
                id = socket.call(session, "catalog_product.create", parameter)
                product.write({'magento_id': int(id)})

                for file in product.magento_images_ids:
                    media_param = []
                    media_param.append(str(product.magento_id))
                    medias = {}
                    medias_list = {}
                    medias_list['content'] = str(file.datas)
                    medias_list['mime'] = str(file.mimetype)
                    medias_list['name'] = str(file.name)
                    medias['file'] = medias_list
                    medias['label'] = str(file.description)
                    medias['position'] = str(file.sortable)

                    media_param.append(medias)
                    media_param.append('1')
                    media_param.append('slxxmckdoe')
                    media_result = socket.call(session, "catalog_product_attribute_media.create",
                                               media_param)
                    print media_result

    def export_sale_order_status(self):
        magento_settings = self.magento_web_shop_ids
        if magento_settings and magento_settings.enable_syncing_to_magento:
            socket, session = self.connection()
            order_ids = self.env['sale.order'].search([('magento_id', '!=', False)])
            for order in order_ids:
                sale_param = []
                sale_param.append(str(order.magento_id))
                if order.state == 'cancel':
                    sale_param.append(str('canceled'))
                if order.state == 'sale':
                    sale_param.append(str('complete'))
                if order.state == 'sent':
                    sale_param.append(str('processing'))
                if order.state == 'draft':
                    sale_param.append(str('pending'))
                if order.magento_comment:
                    sale_param.append(str(order.magento_comment))
                socket.call(session, "sales_order.addComment", sale_param)

    def export_customer(self):
        magento_settings = self.magento_web_shop_ids

        if magento_settings and magento_settings.enable_syncing_to_magento:
            socket, session = self.connection()
            customer_ids = self.env['res.partner'].search(
                ['&', ('magento_id', '=', False), ('customer', '=', True)])
            for customer in customer_ids:
                vals = {}
                if customer.email:
                    vals['email'] = customer.email
                magento_settings = self.getSettings()
                if not customer.email and magento_settings.magento_customer_email:
                    vals['email'] = magento_settings.magento_customer_email
                if not magento_settings.magento_customer_email and not customer.email:
                    vals['email'] = 'demo@demo.com'
                if customer.name:
                    vals['firstname'] = customer.name
                if customer.website_id:
                    vals['website_id'] = str(customer.website_id)
                if customer.store_id:
                    vals['store_id'] = str(customer.store_id.magento_id)
                if customer.mfirstname:
                    vals['firstname'] = customer.mfirstname
                if customer.mlastname:
                    vals['lastname'] = customer.mlastname
                if customer.mpassword:
                    vals['password'] = customer.mpassword
                if customer.mgender:
                    vals['gender'] = customer.mgender
                if customer.mmiddlename:
                    vals['mmiddlename'] = customer.mmiddlename
                if customer.magento_group:
                    vals['group_id'] = str(customer.magento_group.magento_group_id)

                try:
                    id = socket.call(session, "customer.create", [vals])
                    customer.write({'magento_id': int(id)})
                except Exception:
                    print('s')


def get_incremental_filter(magento_settings, import_type):
    import pytz
    today = datetime.datetime.now(pytz.utc)
    interval_units = magento_settings['import_' + import_type + '_interval_units']
    interval_time = magento_settings['import_' + import_type + '_interval_time']
    if interval_units == 'minutes':
        from_date = datetime.timedelta(minutes=int(interval_time) * 3)
    elif interval_units == 'hours':
        from_date = datetime.timedelta(hours=int(interval_time) * 2)
    elif interval_units == 'days' or interval_units == 'workdays':
        from_date = datetime.timedelta(days=int(interval_time) * 2)
    elif interval_units == 'weeks':
        from_date = datetime.timedelta(weeks=int(interval_time) * 2)
    elif interval_units == 'months':
        from_date = datetime.timedelta(days=int(interval_time) * 30 * 2)
    else:
        from_date = datetime.timedelta(hours=1 * 2)

    today = today + datetime.timedelta(hours=int(magento_settings.magento_time_zone_adjustment))
    filters = {'updated_at':
        {
            'from': (today - from_date).strftime("%Y-%m-%d %H:%M:%S"),
            'to': today.strftime("%Y-%m-%d %H:%M:%S")
        },
    }
    return filters
