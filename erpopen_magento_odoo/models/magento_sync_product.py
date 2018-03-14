# -*- coding: utf-8 -*-

import base64
import random
import logging
import threading
import sys, os

import datetime

import psycopg2
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
    _inherit = 'magento.sync'

    def process_product_list(self, product_list, socket, session, delete_barcode=False):
        # self = self.db_cursor_check()
        # self.log(LOGLEVEL.info, 'product', "still " + str(list_size) + " products todo, list size in this thread: " + str(len(product_list)))
        product_obj = self.env['product.product']

        for product in product_list:
            vals = {}
            try:

                exist = product_obj.search([('magento_id', '=', product['product_id'])])
                if not exist:
                    exist = product_obj.search(
                        ['&', ('magento_id', '=', product['product_id']), ('active', '=', False)])
                if 'product_id' in product:
                    extra_info = socket.call(session, 'catalog_product.info',
                                             [str(product['product_id'])])

                    category = self.env['product.public.category'].search(
                        [('magento_id', 'in', extra_info['category_ids'])])
                    if 'sku' in extra_info:
                        print "sku in extra info: " + extra_info['sku']
                        vals['default_code'] = extra_info['sku']
                    elif 'sku' in product:
                        print "sku in product: " + extra_info['sku']
                        vals['default_code'] = product['sku']
                    else:
                        raise Exception("no default code found in product: " + extra_info.name)
                    if 'product_id' in extra_info:
                        vals['magento_id'] = int(extra_info['product_id'])
                    if 'name' in extra_info:
                        vals['name'] = extra_info['name']
                    if 'price' in extra_info:
                        if isinstance(extra_info['price'], str):
                            vals['magento_special_price'] = float(
                                extra_info['price'])  # weird mapping for sanitairkamer
                            vals['list_price'] = float(
                                extra_info['price'])  # weird mapping for sanitairkamer
                    if category:
                        vals['public_categ_ids'] = int(category[0].id)

                    categories = []
                    category_id = False
                    for category in extra_info['category_ids']:
                        category_id = self.env['product.public.category'].search(
                            [('magento_id', '=', int(category))])
                        if category_id:
                            categories.append((4, int(category_id.id)))
                    vals['magento_category_ids'] = categories
                    vals['public_categ_ids'] = categories
                    if category_id and len(category_id) > 1:
                        category_id = category_id[0]
                    if category_id and category_id.product_categ and category_id.product_categ.id:
                        vals['categ_id'] = category_id.product_categ.id
                    if 'description' in extra_info:
                        vals['magento_description'] = extra_info['description']
                    if 'status' in extra_info:
                        if extra_info['status'] == '2':
                            vals['magento_status'] = False
                            # vals['active'] = False
                        else:
                            vals['magento_status'] = True
                            # vals['magento_status'] = bool(extra_info['status'])
                            # vals['active'] = True
                    if 'weight' in extra_info:
                        vals['magento_weight'] = extra_info['weight']
                    if 'visibility' in extra_info:
                        if extra_info['visibility'] == '0':
                            vals['magento_visibility'] = False
                        else:
                            vals['magento_visibility'] = bool(extra_info['visibility'])
                    if 'special_price' in extra_info:
                        if extra_info['special_price'] >= 0:
                            vals['list_price'] = float(
                                extra_info['special_price'])  # weird mapping for sanitairkamer
                            if vals['list_price'] == 0:
                                self.log(LOGLEVEL.error, 'product',
                                         str(extra_info))
                    elif 'price' in extra_info:
                        if extra_info['price'] >= 0:
                            vals['list_price'] = float(
                                extra_info['price'])  # weird mapping for sanitairkamer
                    if 'set' in extra_info:
                        set_id = self.env['magento.attribute.set'].search(
                            [('magento_id', '=', int(extra_info['set']))])
                        if set_id:
                            vals['magento_set'] = int(set_id.id)
                            product_attribute_ids = self.env['product.attribute'].search(
                                [('name', 'in', extra_info.keys())])
                            vals['attribute_value_ids'] = []
                            for product_attribute in product_attribute_ids:
                                if product_attribute.name in extra_info and extra_info[
                                    product_attribute.name] and type(
                                    extra_info[product_attribute.name]) is not list:
                                    product_attribute_value_ids = self.env[
                                        'product.attribute.value'].search(
                                        ['&', ('attribute_id', '=', product_attribute.id),
                                         ('name', '=', extra_info[product_attribute.name])])
                                    if product_attribute_value_ids.id:
                                        vals['attribute_value_ids'].append(
                                            product_attribute_value_ids.id)
                                    else:
                                        pavObject = self.env['product.attribute.value']
                                        new_product_attribute_value_id = pavObject.create(
                                            {'attribute_id': product_attribute.id,
                                             'name': extra_info[product_attribute.name]})
                                        vals['attribute_value_ids'].append(
                                            new_product_attribute_value_id.id)
                            vals['attribute_value_ids'] = [(6, 0, vals['attribute_value_ids'])]
                    if 'type_id' in extra_info and extra_info['type_id'] is not None:
                        type_id = self.env['magento.product.type'].search(
                            [('type', '=', str(extra_info['type_id']))])
                        if type_id:
                            vals['magento_type'] = int(type_id.id)
                        if not exist:
                            if extra_info['type_id'] == 'bundle' or extra_info[
                                'type_id'] == 'configurable':
                                vals['type'] = 'service'
                            else:
                                vals['type'] = 'product'
                    if 'type_id' in extra_info:
                        type_id = self.env['magento.product.type'].search(
                            [('type', '=', str(extra_info['type_id']))])
                        if type_id:
                            vals['magento_type'] = int(type_id.id)
                    if 'special_price' in extra_info:
                        if extra_info['special_price'] is not None:
                            vals['price'] = float(extra_info['special_price'])
                    if 'special_from_date' in extra_info:
                        if extra_info['special_from_date'] is not None:
                            vals['magento_special_from_date'] = str(
                                extra_info['special_from_date'])
                    if 'special_to_date' in extra_info:
                        if extra_info['special_to_date'] is not None:
                            vals['magento_special_to_date'] = str(extra_info['special_to_date'])
                    if 'meta_title' in extra_info:
                        try:
                            vals['magento_meta_title'] = str(extra_info['meta_title'])
                        except:
                            print('non convertito')
                    if 'meta_description' in extra_info:
                        description = extra_info['meta_description']
                        vals['magento_meta_description'] = description
                    if 'meta_keyword' in extra_info:
                        try:
                            vals['magento_meta_keyword'] = str(extra_info['meta_keyword'])
                        except:
                            print('non convertito')
                    if 'custom_design' in extra_info:
                        vals['magento_custom_design'] = str(extra_info['custom_design'])
                    if 'ean_nieuw' in extra_info and extra_info['ean_nieuw'] is not None:
                        vals['barcode'] = str(extra_info['ean_nieuw'])
                    if 'ean' in extra_info and extra_info['ean'] is not None:
                        vals['barcode'] = str(extra_info['ean'])
                    if 'barcode' in vals and vals['barcode']:
                        barcode_exists = self.env['product.product'].search(
                            [('barcode', '=', vals['barcode'])])
                        if not barcode_exists:
                            self.env['product.product'].search(
                                ['&', ('barcode', '=', vals['barcode']), ('active', '=', False)])
                        if barcode_exists and barcode_exists.ids:
                            vals['barcode'] = None
                    if delete_barcode and 'barcode' in vals and vals['barcode']:
                        vals['barcode'] = None
                    if 'cost' in extra_info and extra_info['cost'] is not None:
                        vals['standard_price'] = float(
                            extra_info['cost'])  # todo: moet een een functie worden
                    if 'leverancier' in extra_info:
                        leveranciers = socket.call(session, 'product_attribute.options',
                                                   ["leverancier"])
                        for leverancier in leveranciers:
                            if leverancier['value'] == extra_info['leverancier']:
                                supplier_name = leverancier['label']
                                supplier_partner = self.env['res.partner'].search(
                                    [('name', '=', supplier_name)])
                                if len(supplier_partner.ids) > 1:
                                    supplier_partner = supplier_partner[0]
                                supplier = self.env['product.supplierinfo'].search(
                                    [('name', '=', supplier_partner.id)]).sorted(key=lambda r: r.id)
                                if len(supplier.ids) > 1:
                                    supplier = supplier[0]
                                if supplier and 'cost' in extra_info and extra_info[
                                    'cost'] is not None and supplier.price != float(
                                    extra_info['cost']):
                                    if not exist:
                                        product_supplierinfo_object = self.env[
                                            'product.supplierinfo']
                                        cost = 0.0
                                        if 'cost' in extra_info and extra_info['cost'] is not None:
                                            cost = float(extra_info['cost'])
                                            supplier = product_supplierinfo_object.create(
                                                {'display_name': leverancier['label'],
                                                 'name': supplier_partner.id,
                                                 'price': cost})
                                            vals['seller_ids'] = [(4, supplier.id)]
                                        else:
                                            supplier.write({'price': float(extra_info[
                                                                               'cost'])})  # todo: price wegschrijven als het product geupdate wordt.
                                if not supplier.id:
                                    partner_obj = self.env['res.partner']
                                    new_supplier_partner = partner_obj.create(
                                        {'name': leverancier['label'],
                                         'supplier': True})
                                    product_supplierinfo_object = self.env[
                                        'product.supplierinfo']
                                    cost = 0.0
                                    if 'cost' in extra_info and extra_info['cost'] is not None:
                                        cost = float(extra_info['cost'])
                                    new_supplier = product_supplierinfo_object.create(
                                        {'display_name': leverancier['label'],
                                         'name': new_supplier_partner.id,
                                         'price': cost})
                                    vals['seller_ids'] = [(4, new_supplier.id)]
                                else:
                                    vals['seller_ids'] = [(4, supplier.id)]
                                print extra_info[
                                          'name'] + " leverancier toegevoegd: " + supplier_name

                    vals['magento_import'] = True
                    vals['magento_sync'] = True

                    vals['company_id'] = self.magento_web_shop_ids.company.id
                    if not exist:  # todo: als inactief, eerst actief doorvoeren. dan inactief zetten en als 1 product.product van de product.template ook de template op inactief zetten.
                        product_id = product_obj.create(vals)
                        print("Product " + product_id.name + " created")
                    else:
                        exist.write(vals)
                        product_id = exist
                        print("Product " + product_id.name + " updated")

                    self.product_images(product_id.magento_id)

                    self.env.cr.commit()
                else:
                    print 'no product id'
                    logging.info("No product id in product")
            except psycopg2.IntegrityError as e:
                if "product_product_barcode_uniq" in e.message:
                    self.log(LOGLEVEL.warning, 'product', "dubplicate barcode" + str(e))
                    self.process_product_list(product_list, socket, session, True)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                self.log(LOGLEVEL.error, 'product',
                         "Something went wrong with the product creation/update with error: " + format(
                             (exc_type, fname, exc_tb.tb_lineno)) + str(e))
            except IOError, e:
                print e
            except xmlrpclib.Fault, e:
                logging.info("Something went wrong with product id [%s] erorr: [%s]",
                             product['product_id'], e)
                logging.exception("message")
            finally:
                print 'done with product'

    def process_product_list_only_adding(self, product_list, socket, session):
        # self = self.db_cursor_check()
        # self.log(LOGLEVEL.info, 'product', "still " + str(list_size) + " products todo, list size in this thread: " + str(len(product_list)))
        product_obj = self.env['product.product']

        for product in product_list:
            try:
                vals = {}
                exist = product_obj.search([('magento_id', '=', product['product_id'])])
                if not exist and 'sku' in product:
                    exist = product_obj.search([('default_code', '=', product['sku'])])
                    if not exist:
                        exist = product_obj.search(
                            ['&', ('active', '=', False), ('default_code', '=', product['sku'])])
                if 'product_id' in product:
                    extra_info = socket.call(session, 'catalog_product.info',
                                             [str(product['product_id'])])

                    if 'sku' in extra_info:
                        print extra_info['sku']
                        vals['default_code'] = extra_info['sku']
                    elif 'sku' in product:
                        print extra_info['sku']
                        vals['default_code'] = product['sku']
                    else:
                        raise Exception("no default code found in product: " + extra_info.name)

                    if not exist:
                        category = self.env['product.public.category'].search(
                            [('magento_id', '=', extra_info['category_ids'])])

                        if 'product_id' in extra_info:
                            vals['magento_id'] = int(extra_info['product_id'])
                        if 'name' in extra_info:
                            vals['name'] = extra_info['name']
                        if 'price' in extra_info:
                            if isinstance(extra_info['price'], str):
                                vals['magento_special_price'] = float(
                                    extra_info['price'])  # weird mapping for sanitairkamer
                        if category:
                            vals['public_categ_ids'] = int(category[0].id)

                        categories = []
                        category_id = False
                        for category in extra_info['category_ids']:
                            category_id = self.env['product.public.category'].search(
                                [('magento_id', '=', int(category))])
                            if category_id:
                                categories.append((4, int(category_id.id)))
                        vals['magento_category_ids'] = categories
                        vals['public_categ_ids'] = categories
                        if category_id and len(category_id) > 1:
                            category_id = category_id[0]
                        if category_id and category_id.product_categ and category_id.product_categ.id:
                            vals['categ_id'] = category_id.product_categ.id
                        if 'description' in extra_info:
                            vals['magento_description'] = extra_info['description']
                        if 'status' in extra_info:
                            if extra_info['status'] == '2':
                                vals['magento_status'] = False
                                # vals['active'] = False
                            else:
                                vals['magento_status'] = True

                                # vals['magento_status'] = bool(extra_info['status'])
                                # vals['active'] = True
                        if 'weight' in extra_info:
                            vals['magento_weight'] = extra_info['weight']
                        if 'visibility' in extra_info:
                            if extra_info['visibility'] == '0':
                                vals['magento_visibility'] = False
                            else:
                                vals['magento_visibility'] = bool(extra_info['visibility'])
                        if 'special_price' in extra_info:
                            if extra_info['special_price'] >= 0:
                                vals['list_price'] = float(
                                    extra_info['special_price'])  # weird mapping for sanitairkamer
                        if 'set' in extra_info:
                            set_id = self.env['magento.attribute.set'].search(
                                [('magento_id', '=', int(extra_info['set']))])
                            if set_id:
                                vals['magento_set'] = int(set_id.id)
                                product_attribute_ids = self.env['product.attribute'].search(
                                    [('name', 'in', extra_info.keys())])
                                vals['attribute_value_ids'] = []
                                for product_attribute in product_attribute_ids:
                                    if product_attribute.name in extra_info and extra_info[
                                        product_attribute.name] and type(
                                        extra_info[product_attribute.name]) is not list:
                                        product_attribute_value_ids = self.env[
                                            'product.attribute.value'].search(
                                            ['&', ('attribute_id', '=', product_attribute.id),
                                             ('name', '=', extra_info[product_attribute.name])])
                                        if product_attribute_value_ids.id:
                                            vals['attribute_value_ids'].append(
                                                product_attribute_value_ids.id)
                                        else:
                                            pavObject = self.env['product.attribute.value']
                                            new_product_attribute_value_id = pavObject.create(
                                                {'attribute_id': product_attribute.id,
                                                 'name': extra_info[product_attribute.name]})
                                            vals['attribute_value_ids'].append(
                                                new_product_attribute_value_id.id)
                                vals['attribute_value_ids'] = [(6, 0, vals['attribute_value_ids'])]
                        if 'type_id' in extra_info and extra_info['type_id'] is not None:
                            type_id = self.env['magento.product.type'].search(
                                [('type', '=', str(extra_info['type_id']))])
                            if type_id:
                                vals['magento_type'] = int(type_id.id)
                            if not exist:
                                if extra_info['type_id'] == 'bundle' or extra_info[
                                    'type_id'] == 'configurable':
                                    vals['type'] = 'service'
                                else:
                                    vals['type'] = 'product'
                        if 'type_id' in extra_info:
                            type_id = self.env['magento.product.type'].search(
                                [('type', '=', str(extra_info['type_id']))])
                            if type_id:
                                vals['magento_type'] = int(type_id.id)
                        if 'special_price' in extra_info:
                            if extra_info['special_price'] is not None:
                                vals['price'] = float(extra_info['special_price'])
                        if 'special_from_date' in extra_info:
                            if extra_info['special_from_date'] is not None:
                                vals['magento_special_from_date'] = str(
                                    extra_info['special_from_date'])
                        if 'special_to_date' in extra_info:
                            if extra_info['special_to_date'] is not None:
                                vals['magento_special_to_date'] = str(extra_info['special_to_date'])
                        if 'meta_title' in extra_info:
                            try:
                                vals['magento_meta_title'] = str(extra_info['meta_title'])
                            except:
                                print('non convertito')
                        if 'meta_description' in extra_info:
                            description = extra_info['meta_description']
                            vals['magento_meta_description'] = description
                        if 'meta_keyword' in extra_info:
                            try:
                                vals['magento_meta_keyword'] = str(extra_info['meta_keyword'])
                            except:
                                print('non convertito')
                        if 'custom_design' in extra_info:
                            vals['magento_custom_design'] = str(extra_info['custom_design'])
                        if 'ean_nieuw' in extra_info and extra_info['ean_nieuw'] is not None:
                            vals['barcode'] = str(extra_info['ean_nieuw'])
                        if 'ean' in extra_info and extra_info['ean'] is not None:
                            vals['barcode'] = str(extra_info['ean'])
                        if 'barcode' in vals and vals['barcode']:
                            barcode_exists = self.env['product.product'].search(
                                [('barcode', '=', str(vals['barcode']))])
                            if barcode_exists and barcode_exists.ids:
                                vals['barcode'] = None
                            else:
                                barcode_exists = self.env['product.product'].search(
                                    ['&', ('active', '=', False),
                                     ('barcode', '=', str(vals['barcode']))])
                                if barcode_exists and barcode_exists.ids:
                                    vals['barcode'] = None
                        if 'cost' in extra_info and extra_info['cost'] is not None:
                            vals['standard_price'] = float(extra_info['cost'])
                    if 'leverancier' in extra_info:
                        leveranciers = socket.call(session, 'product_attribute.options',
                                                   ["leverancier"])
                        for leverancier in leveranciers:
                            if leverancier['value'] == extra_info['leverancier']:
                                supplier_name = leverancier['label']
                                supplier_partner = self.env['res.partner'].search(
                                    [('name', '=', supplier_name)])
                                if len(supplier_partner.ids) > 1:
                                    supplier_partner = supplier_partner[0]
                                supplier = self.env['product.supplierinfo'].search(
                                    [('name', '=', supplier_partner.id)])
                                if len(supplier.ids) > 1:
                                    supplier = supplier[0]
                                if supplier and 'cost' in extra_info and extra_info[
                                    'cost'] is not None and supplier.price != float(
                                    extra_info['cost']):
                                    if not exist:
                                        product_supplierinfo_object = self.env[
                                            'product.supplierinfo']
                                        cost = 0.0
                                        if 'cost' in extra_info and extra_info['cost'] is not None:
                                            cost = float(extra_info['cost'])
                                            supplier = product_supplierinfo_object.create(
                                                {'display_name': leverancier['label'],
                                                 'name': supplier_partner.id,
                                                 'price': cost})
                                            vals['seller_ids'] = [(4, supplier.id)]
                                        else:
                                            supplier.write({'price': float(extra_info['cost'])})
                                if not supplier.id:
                                    partner_obj = self.env['res.partner']
                                    new_supplier_partner = partner_obj.create(
                                        {'name': leverancier['label'],
                                         'supplier': True})
                                    product_supplierinfo_object = self.env[
                                        'product.supplierinfo']
                                    cost = 0.0
                                    if 'cost' in extra_info and extra_info['cost'] is not None:
                                        cost = float(extra_info['cost'])
                                    new_supplier = product_supplierinfo_object.create(
                                        {'display_name': leverancier['label'],
                                         'name': new_supplier_partner.id,
                                         'price': cost})
                                    vals['seller_ids'] = [(4, new_supplier.id)]
                                else:
                                    vals['seller_ids'] = [(4, supplier.id)]
                                print extra_info[
                                          'name'] + " leverancier toegevoegd: " + supplier_name

                    vals['magento_import'] = True
                    vals['magento_sync'] = True
                    vals['company_id'] = self.magento_web_shop_ids.company.id
                    product_id = False
                    if not exist:
                        product_id = product_obj.create(vals)
                        print("Product " + product_id.name + " created")
                    else:
                        exist.write(vals)
                        product_id = exist
                        print("Product " + product_id.name + " updated")

                    self.product_images(product_id.magento_id)

                    self.env.cr.commit()
                else:
                    print 'no product id'
                    logging.info("No product id in product")
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                self.log(LOGLEVEL.error, 'product',
                         "Something went wrong with the product creation/update of " + product[
                             'name'] + "with barcode: " + vals[
                             'barcode'] + " with error: " + format(
                             (exc_type, fname, exc_tb.tb_lineno)) + str(e))
            except IOError, e:
                print e
            except xmlrpclib.Fault, e:
                logging.info("Something went wrong with product id [%s] erorr: [%s]",
                             product['product_id'], e)
                logging.exception("message")
            finally:
                print 'done with product'

    def single_product(self, magento_id):
        filters = {'product_id': str(magento_id)}
        self.log(LOGLEVEL.info, 'Single product', "started single product import")
        magento_settings = self.magento_web_shop_ids
        socket, session = self.connection()
        products_list = socket.call(session, "catalog_product.list", [filters])
        split_list = [products_list]
        for list in split_list:
            socket, session = self.connection()
            if len(list) > 0:
                t = threading.Thread(target=self.total_product_import,
                                     args=(
                                         list, magento_settings, socket, session,
                                         len(products_list)))
                t.start()
