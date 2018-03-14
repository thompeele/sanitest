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

    def create_customer(self, customer, session, socket):
        exist = self.env['res.partner'].search(
            ['&', ('type', '=', 'contact'), ('magento_id', '=', int(customer['customer_id']))])
        customer_info = socket.call(session, "customer.info", [customer['customer_id']])
        customer_address = socket.call(session, "customer_address.list", [customer['customer_id']])
        vals = {}
        vals['company_id'] = self.magento_web_shop_ids.company.id
        if customer_address:
            customer_address = customer_address[0]
        if 'company' in customer_address:
            vals['is_company'] = True
        if 'fax' in customer_address:
            vals['fax'] = customer_address['fax']
        if 'postcode' in customer_address:
            vals['zip'] = customer_address['postcode']
        # if 'region' in customer_address:
        if 'city' in customer_address:
            vals['city'] = customer_address['city']
        if 'street' in customer_address:
            vals['street'] = customer_address['street']
            if 'suffix' in customer_address and customer_address['suffix'] is not None:
                vals['street'] += customer_address['suffix']
        if 'telephone' in customer_address:
            vals['phone'] = customer_address['telephone']
        if 'email' in customer:
            vals['email'] = customer['email']
        if 'firstname' in customer:
            vals['name'] = customer['firstname'] + " " + customer['lastname']
        if 'taxvat' in customer_info:
            vals['vat'] = self.check_vat(customer_info['taxvat'])
        if 'group_id' in customer_info:
            group_id = self.env['magento.customers.group'].search(
                [('magento_group_id', '=', int(customer_info['group_id']))])
            if group_id:
                vals['magento_group'] = int(group_id.id)
        if 'customer_id' in customer:
            vals['magento_id'] = customer['customer_id']
        if 'store_id' in customer_info:
            store = self.env['magento.store'].search(
                [('magento_id', '=', int(customer_info['store_id']))])
            if store:
                vals['store_id'] = store.id
        if 'website_id' in customer_info:
            vals['website_id'] = customer_info['website_id']
        if 'firstname' in customer_info:
            vals['mfirstname'] = customer_info['firstname']
        if 'lastname' in customer_info:
            vals['mlastname'] = customer_info['lastname']
        if 'password' in customer_info:
            vals['mpassword'] = customer_info['password']
        if 'gender' in customer_info:
            if customer_info['gender'] is not None:
                vals['mgender'] = int(customer_info['gender'])
        if 'middlename' in customer_info:
            vals['mmiddlename'] = customer_info['middlename']
        if customer_address:
            country_list = socket.call(session, "directory_country.list")
            for country in country_list:
                if country['country_id'] == customer_address['country_id']:
                    country_id = self.env['res.country'].search(
                        [('code', '=', country['iso2_code'])])
                    if country_id:
                        vals['country_id'] = int(country_id.id)
                        country_id.write({'magento_id': str(country['country_id'])})

            region_list = socket.call(session, "directory_region.list",
                                      [customer_address['country_id']])
            for region in region_list:
                if region['region_id'] == customer_address['region_id']:
                    state_id = self.env['res.country.state'].search([('code', '=', region['code'])])
                    if state_id:
                        vals['state_id'] = int(state_id[0].id)
                        state_id[0].write({'magento_id': str(region['region_id'])})
        if not exist:
            return self.env['res.partner'].create(vals)
        else:
            exist.write(vals)
            return exist