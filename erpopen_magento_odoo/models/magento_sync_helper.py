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
    _inherit = 'magento.sync'

    def connection(self):
        magento_settings = self.magento_web_shop_ids
        if not magento_settings.url:
            raise osv.except_osv("Warning!", " Configure Magento Settings")
        else:
            socket = xmlrpclib.ServerProxy(magento_settings.url + "/index.php/api/xmlrpc")
            try:
                session = socket.login(magento_settings.username, magento_settings.password)
                return socket, session
            # except:
            #     raise osv.except_osv(('Error'), (
            #         'Can not connect to magento. verify entries made in the settings.'))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                self.log(LOGLEVEL.error, 'connection problem',
                         "Something went wrong with the connection with error: " + format(
                             (exc_type, fname, exc_tb.tb_lineno, str(e))))

    def getSettings(self):
        magento_settings = self.magento_web_shop_ids
        if not magento_settings:
            magento_settings = self.env['magento.settings'].create({})
        return magento_settings

    def random(self, length):
        return ''.join(random.choice(string.lowercase) for i in range(length))

    def export_stock(self):
        magento_settings = self.magento_web_shop_ids

        if magento_settings and magento_settings.enable_syncing_to_magento:
            socket, session = self.connection()
            product_ids = self.env['product.product'].search([('magento_id', '!=', False)])

            for product in product_ids:
                parameter = []
                datas = {}
                stock_data = {}
                product_uom_qty_ids = self.env['stock.quant'].search(
                    [('product_id', '=', int(product.id))])
                if product_uom_qty_ids:
                    sum = 0
                    for product_qty in product_uom_qty_ids:
                        sum += product_qty.qty
                    stock_data['qty'] = str(sum)
                else:
                    stock_data['qty'] = '0'
                datas['stock_data'] = stock_data

                parameter.append(str(product.magento_id))
                parameter.append(datas)
                parameter.append('1')
                parameter.append(self.random(10))
                id = socket.call(session, "catalog_product.update", parameter)

    def total_product_import(self, list, magento_settings, socket, session, len_big_list, new=False):
        new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        uid, context = self.env.uid, self.env.context
        with api.Environment.manage():
            new_cr.autocommit(True)
            self = self.with_env(self.env(cr=new_cr)).with_context(original_cr=self._cr)
            self.log(LOGLEVEL.info, 'product', "still " + str(len_big_list) + " products todo, list size in this thread: " + str(len(list)))
            if new:
                self.process_product_list_only_adding(list, socket, session)
            else:
                self.process_product_list(list, socket, session)
            self.log(LOGLEVEL.info, 'product', "done with products still " + str(len_big_list - len(list)) + " in list ")
            self.env.cr.close()

    def product_images(self, magento_id=None):
        socket, session = self.connection()
        if magento_id is None:
            magento_product_ids = self.env['product.product'].search([('magento_id', '!=', False)])
        else:
            self.env.cr.execute('delete from ir_attachment where magento_id = %i' % magento_id)
            magento_product_ids = self.env['product.product'].search([('magento_id', '=', magento_id)])
        for product in magento_product_ids:
            media = socket.call(session, 'catalog_product_attribute_media.list',
                                [str(product['magento_id'])])
            images = []
            base64_array = []
            for photo in media:
                if 'url' in photo:
                    url = photo['url']
                    filename = url.split('/')[-1]
                    file = requests.get(str(url), stream=True)
                    if file.status_code == 200:
                        vals_p = {'datas': base64.b64encode(file.content),
                                  'name': filename,
                                  'url': url,
                                  'datas_fname': filename,
                                  'res_model': 'product.template',
                                  'magento_id': product.magento_id,
                                  'res_id': 0}

                        base64_array.append(vals_p)
                        exist = self.env['ir.attachment'].search([('name', '=', filename)])
                        if not exist:
                            attachment = self.env['ir.attachment'].create(vals_p)
                            if attachment:
                                images.append((4, int(attachment.id)))
                        else:
                            if len(exist.ids) > 1:
                                exist = exist[0]
                            exist.write(vals_p)

            product.write({'magento_images_ids': images, 'magento_import': True})

            image_type = ['image', 'image_medium', 'image_small']
            if len(base64_array) > 0:
                first_photo = base64_array[0]
                first_photo['res_model'] = 'product.template'
                esiste_foto_prodotto = self.env['ir.attachment'].search(
                    ['&', ('res_model', '=', 'product.template'), ('res_id', '=', int(product.id))])
                product_id = self.env['product.product'].search([('id', '=', int(int(product.id)))])
                esiste_foto_template = False
                if product_id:
                    esiste_foto_template = int(product_id.product_tmpl_id)
                    first_photo['res_id'] = int(product_id.product_tmpl_id)
                for type in image_type:
                    first_photo['res_field'] = type
                    first_photo['name'] = type
                    if esiste_foto_prodotto and esiste_foto_template:
                        esiste_foto_prodotto.write(first_photo)
                    if not esiste_foto_prodotto and esiste_foto_template:
                        self.env['ir.attachment'].create(first_photo)

    def log(self, level, name, text):
        self.check_current_model()
        if 'cursor' in text and 'closed' in text:
            new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
            uid, context = self.env.uid, self.env.context
            # with api.Environment.manage():
            new_cr.autocommit(True)
            self = self.with_env(self.env(cr=new_cr)).with_context(original_cr=self._cr)
        # self = self.db_cursor_check()
        if level.value == LOGLEVEL.info.value:
            logging.info(str(name) + ' - ' + str(text))
            level_string = 'Info'
        elif level.value == LOGLEVEL.warning.value:
            logging.warning(str(name) + ' - ' + str(text))
            level_string = 'Warning'
        else:
            logging.error(str(name) + ' - ' + str(text))
            level_string = 'Error'
        print level_string + ' - ' + str(self.magento_web_shop_ids.name + " - " + name) + ' - ' + str(text)
        self.env['magento.error.log'].create({'level': level_string,
                                              'name': name,
                                              'company_id': self.magento_web_shop_ids.company.id,
                                              'message': str(text)})

    def split_list(self, list, n):
        avg = len(list) / float(n)
        out = []
        last = 0.0

        while last < len(list):
            out.append(list[int(last):int(last + avg)])
            last += avg

        return out

    def recursive_category(self, category):
        categories_obj = self.env['product.public.category']
        exist = categories_obj.search([('magento_id', '=', int(category['category_id']))])
        parent_id = categories_obj.search([('magento_id', '=', int(category['parent_id']))])
        if parent_id:
            vals = {
                'name': str(category['name']),
                'parent_id': int(parent_id.id),
                'magento_id': int(category['category_id'])
            }
        else:
            vals = {
                'name': str(category['name']),
                'parent_id': False,
                'magento_id': int(category['category_id'])
            }
        if not exist:
            categories_obj.create(vals)
        else:
            exist.write(vals)

        for child in category['children']:
            self.recursive_category(child)

    def stock_magento(self):
        socket, session = self.connection()
        elenco_prodotti = []
        product_ids = self.env['product.product'].search([('magento_id', '!=', False)])
        for product in product_ids:
            elenco_prodotti.append(str(product.magento_id))
        stock_list = socket.call(session, "cataloginventory_stock_item.list", [elenco_prodotti])

        vals = {'name': "Magento Inventory", 'filter': "partial"}

        id_inventory = self.env['stock.inventory'].create(vals)
        id_inventory.prepare_inventory()

        line = []
        for stock in stock_list:
            for product in product_ids:
                if str(product.magento_id) == (stock['product_id']):
                    # settings
                    if float(stock['qty']) >= 0:
                        line.append(
                            (0, 0,
                             {'product_id': int(product.id), 'product_qty': float(stock['qty']),
                              'location_id': 15,
                              'company_id': 1,
                              'inventory_id': int(id_inventory.id),
                              'product_uom_id': 1}))

        vals['line_ids'] = line
        id_inventory.write(vals)
        id_inventory.action_done()

    def check_current_model(self, id=1):
        if self.id and self.id != id:
            self = self.env['magento.sync'].search([("id", "=", id)])
