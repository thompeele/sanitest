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

    def process_sale_order(self, sale_order_list, magento_settings):
        with api.Environment.manage():
            new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
            uid, context = self.env.uid, self.env.context
            new_cr.autocommit(True)
            self = self.with_env(self.env(cr=new_cr)).with_context(original_cr=self._cr)
            self.process_simple_order(sale_order_list)
            if not self.env.cr.closed:
                self.env.cr.close()

    def process_simple_order(self, sale_order_list):
        socket, session = self.connection()
        try:
            logging.info(str(1) + ' - ' + str(self.env.cr.closed))
            sale_order_obj = self.env['sale.order']
            logging.info(str(2) + ' - ' + str(self.env.cr.closed))
            magento_settings = self.magento_web_shop_ids

            for order in sale_order_list:
                sale_order = False
                logging.info(str(3) + ' - ' + str(self.env.cr.closed))
                try:
                    logging.info(str(4) + ' - ' + str(self.env.cr.closed))
                    exist = sale_order_obj.search([('magento_id', '=', str(order['increment_id']))])
                    logging.info(str(5) + ' - ' + str(self.env.cr.closed))
                    if exist and exist.ids and len(exist.ids) > 1:
                        exist = exist[0]
                    if not exist or (
                                        exist and exist.id and exist.state != 'done' and exist.state != 'cancel'):
                        sale_order_info = socket.call(session, "sales_order.info",
                                                      [order['increment_id']])

                        # block sale order if not correctly paid
                        is_correctly_payd = False

                        if 'payment' in sale_order_info and sale_order_info['payment'] and \
                                        sale_order_info['payment'] is not None and len(
                            sale_order_info['payment']) > 5:
                            journal = self.get_journal(sale_order_info['payment'])
                            if not journal:
                                journal = magento_settings.magento_journal_id
                            if sale_order_info['payment']['amount_ordered'] == \
                                    sale_order_info['payment'][
                                        'amount_paid'] or journal.can_pay_in_advance:
                                is_correctly_payd = True
                        if is_correctly_payd:
                            vals = self.get_partners(sale_order_info, session, socket)
                            warehouse_id = self.env['stock.warehouse'].search(
                                [('company_id.id', '=', self.magento_web_shop_ids.company.id)])
                            if warehouse_id and warehouse_id.ids and len(warehouse_id.ids) > 1:
                                warehouse_id = warehouse_id[0]
                            vals['warehouse_id'] = warehouse_id.id
                            vals_invoice = {}
                            vals_invoice['partner_id'] = vals['partner_id']
                            lines = []
                            lines_invoice = []
                            products_to_update = []
                            for product in sale_order_info['items']:
                                products_to_update.append({'product_id': product["product_id"]})
                            self.process_product_list(products_to_update, socket, session)
                            # self = self.db_cursor_check()

                            if not exist:
                                for item in sale_order_info['items']:
                                    product_id = self.env['product.product'].search(
                                        [('magento_id', '=', int(item['product_id']))])
                                    price = float(item['price'])
                                    if 'parent_item_id' in item and item[
                                        'parent_item_id'] is not None:
                                        price = 0.0
                                    if product_id:
                                        product_id = product_id[0]
                                        lines.append(
                                            (0, 0,
                                             {'product_id': int(product_id.id),
                                              'company_id': int(magento_settings.company.id),
                                              'name': item['name'],
                                              'product_uom_qty': float(item['qty_ordered']),
                                              'product_uom': int(product_id.uom_id.id),
                                              'tax_id': False,
                                              'price_unit': price}))
                                        magento_settings = self.magento_web_shop_ids
                                        if magento_settings.magento_sale_order_auto_invoice:
                                            lines_invoice.append(
                                                (0, 0,
                                                 {'product_id': int(product_id.id),
                                                  'company_id': int(magento_settings.company.id),
                                                  'name': item['name'],
                                                  'invoice_line_tax_ids': False,
                                                  'quantity': float(item['qty_ordered']),
                                                  'account_id': int(
                                                      magento_settings.magento_account_id.id),
                                                  'price_unit': price}))
                                        else:
                                            lines_invoice.append(
                                                (0, 0,
                                                 {'product_id': int(product_id.id),
                                                  'company_id': int(magento_settings.company.id),
                                                  'name': item['name'],
                                                  'quantity': float(item['qty_ordered']),
                                                  'account_id': int(0),
                                                  'invoice_line_tax_ids': False,
                                                  'price_unit': price}))
                            else:
                                order_lines = exist.order_line
                                for order_line in order_lines:
                                    item_exists = False
                                    for item in sale_order_info['items']:
                                        if not item_exists and order_line.invoice_lines.ids and str(
                                                order_line.invoice_lines[
                                                    0].product_id.magento_id) == \
                                                item['product_id']:
                                            item_exists = True
                                    if not item_exists and exist.invoice_ids:
                                        order_line.invoice_line_create(exist.invoice_ids[0].id,
                                                                       order_line.qty_to_invoice)
                            new_line = []
                            clean_line = []
                            clean_line.append((5,))
                            new_line.extend(clean_line)
                            new_line.extend(lines)
                            if exist:
                                new_line = (6, 0, exist.order_line.ids)
                            else:
                                vals_invoice['invoice_line_ids'] = lines_invoice
                            if 'status' in sale_order_info:
                                if not exist:
                                    vals['state'] = 'draft'
                            if 'created_at' in sale_order_info:
                                vals['date_order'] = sale_order_info['created_at']
                            vals['magento_id'] = str(order['increment_id'])
                            vals_invoice['magento_id'] = str(order['increment_id'])

                            crm_team_id = self.env['crm.team'].search(
                                [('name', '=', 'Website Sales')])
                            if crm_team_id and magento_settings.magento_sale_order_from_ecommerce:
                                vals['team_id'] = int(crm_team_id[0].id)
                            if 'onestepcheckout_customercomment' in sale_order_info and \
                                            sale_order_info[
                                                'onestepcheckout_customercomment'] is not None:
                                vals['note'] = sale_order_info['onestepcheckout_customercomment']

                            vals["company_id"] = magento_settings.company.id

                            if not exist and 'state' in sale_order_info and sale_order_info[
                                'state'] not in ['canceled',
                                                 'pending_payment'] and 'status' in sale_order_info and \
                                            sale_order_info['status'] not in ['canceled',
                                                                              'icecore_open']:
                                vals['order_line'] = lines
                                sale_order = self.env['sale.order'].create(vals)

                                delivery_carrier = self.env['delivery.carrier'].search(
                                    [('magento_code', '=', sale_order_info['shipping_method'])])
                                if not delivery_carrier:
                                    delivery_carrier_obj = self.env['delivery.carrier']
                                    delivery_carrier = delivery_carrier_obj.create(
                                        {'name': sale_order_info['shipping_description'],
                                         'magento_code': sale_order_info['shipping_method']})
                                if delivery_carrier:
                                    sale_order.carrier_id = delivery_carrier.id
                                    sol_delivery = sale_order._create_delivery_line(
                                        delivery_carrier,
                                        sale_order_info[
                                            'shipping_amount'])
                                    if "id" in sol_delivery:
                                        sale_order.write({'order_line': [(4, sol_delivery.id)]})
                                sale_order._compute_tax_id()
                                logging.info('Created: ' + vals['magento_id'])
                            elif exist:
                                exist.write(vals)
                                sale_order = exist
                                sale_order._compute_tax_id()
                                logging.info('Updated: ' + vals['magento_id'])
                            else:
                                self.log(LOGLEVEL.warning, 'sale order',
                                         "Canceled invoice probably a canceled payment with order id: " +
                                         vals['magento_id'])

                            if sale_order:
                                delivery_carrier = self.env['delivery.carrier'].search(
                                    [('magento_code', '=', sale_order_info['shipping_method'])])
                                if not delivery_carrier:
                                    delivery_carrier_obj = self.env['delivery.carrier']
                                    delivery_carrier_obj.create(
                                        {'name': sale_order_info['shipping_description'],
                                         'magento_code': sale_order_info['shipping_method']})

                                if magento_settings.magento_sale_order_auto_invoice:
                                    exist_invoice = False
                                    if sale_order.state == 'sale' or sale_order.state == 'done':
                                        if sale_order.invoice_ids.ids:
                                            exist_invoice = sale_order.invoice_ids[0]
                                        else:
                                            exist_invoice = self.env['account.invoice'].search(
                                                [('magento_id', '=',
                                                  str(vals_invoice['magento_id']))])
                                        if exist_invoice and not exist_invoice.id:
                                            exist_invoice = False

                                    vals_invoice['account_id'] = int(
                                        magento_settings.magento_account_id.id)
                                    vals_invoice['company_id'] = int(
                                        magento_settings.magento_company_id.id)
                                    vals_invoice['currency_id'] = int(
                                        magento_settings.magento_currency_id.id)
                                    vals_invoice['journal_id'] = int(
                                        magento_settings.magento_journal_id.id)
                                    sale_order_info['payment']['quote_id'] = sale_order_info[
                                        'quote_id']
                                    journal = self.get_journal(sale_order_info['payment'])
                                    if not journal:
                                        journal = magento_settings.magento_journal_id
                                    # vals_invoice['journal_id'] = int(journal)

                                    if journal and journal.additional_costs and journal.additional_costs.id:
                                        journal_fee = journal.additional_costs.get_fee(
                                            sale_order.amount_total - sale_order.delivery_price)
                                        add_new_journal_fee = True
                                        for sale_order_line in sale_order.order_line:
                                            if journal.additional_costs.id == sale_order_line.product_id.id:
                                                add_new_journal_fee = False
                                        if add_new_journal_fee:
                                            if float(sale_order_info[
                                                         'base_fooman_surcharge_amount']) > journal_fee:
                                                journal_fee = sale_order_info[
                                                    'base_fooman_surcharge_amount']
                                            fee_order_line_val = {
                                                'product_id': int(journal.additional_costs.id),
                                                'name': journal.additional_costs.name,
                                                'company_id': self.magento_web_shop_ids.company.id,
                                                'product_uom_qty': 1,
                                                'order_id': sale_order.id,
                                                'product_uom': int(
                                                    journal.additional_costs.uom_id.id),
                                                'tax_id': False,
                                                'price_unit': float(journal_fee)}
                                            fee_order_line = self.env['sale.order.line'].create(
                                                fee_order_line_val)
                                            fee_vals = {'order_line': [(4, fee_order_line.id)]}
                                            sale_order.write(fee_vals)
                                            sale_order._compute_tax_id()

                                if 'status' in sale_order_info:
                                    if exist.state != 'sale' and exist.state != 'done' and exist.state != 'cancel':
                                        if sale_order_info['status'] == 'pending' or \
                                                        sale_order_info[
                                                            'status'] == 'pending_payment' or \
                                                        sale_order_info['status'] == 'processing' or \
                                                        sale_order_info['status'] == 'icecore_open':
                                            sale_order.action_confirm()
                                        if sale_order_info['status'] == 'onhold' and \
                                                        sale_order_info['status'] == 'complete' or \
                                                        sale_order_info['status'] == 'icecore_ok':
                                            sale_order.action_confirm()
                                        if sale_order_info['status'] == 'canceled':
                                            if exist:
                                                exist.action_cancel()

                                    if sale_order.state == 'sale' or sale_order.state == 'done':
                                        if sale_order.invoice_ids.ids:
                                            exist_invoice = sale_order.invoice_ids[0]
                                        else:
                                            exist_invoice = self.env['account.invoice'].search(
                                                [('magento_id', '=',
                                                  str(vals_invoice['magento_id']))])
                                        if not exist_invoice:
                                            new_invoice_id = sale_order.action_invoice_create()
                                            exist_invoice = self.env['account.invoice'].search(
                                                [('id', 'in', new_invoice_id)])
                                        else:
                                            exist_invoice.write(vals_invoice)
                                        if exist_invoice:
                                            exist_invoice.compute_taxes()

                                            if exist_invoice.state == 'draft' or exist_invoice.state == 'proforma' or exist_invoice.state == 'proforma2':
                                                if sale_order_info['status'] == 'pending' or \
                                                                sale_order_info[
                                                                    'status'] == 'pending_payment' or \
                                                                sale_order_info[
                                                                    'status'] == 'processing' or \
                                                                sale_order_info[
                                                                    'status'] == 'icecore_open' or \
                                                                sale_order_info[
                                                                    'status'] == 'onhold':
                                                    exist_invoice.action_invoice_open()
                                                    exist_invoice.compute_taxes()
                                                if sale_order_info['status'] == 'complete' or \
                                                                sale_order_info[
                                                                    'status'] == 'icecore_ok':
                                                    exist_invoice.action_invoice_open()
                                                    exist_invoice.compute_taxes()
                                                    self.register_payment(exist_invoice,
                                                                          sale_order_info)
                                                if sale_order_info['status'] == 'canceled':
                                                    if exist:
                                                        exist.action_cancel()
                                            elif exist_invoice.state == 'open':
                                                if sale_order_info['status'] == 'complete' or \
                                                                sale_order_info[
                                                                    'status'] == 'icecore_ok':
                                                    exist_invoice.compute_taxes()
                                                    self.register_payment(exist_invoice,
                                                                          sale_order_info)
                                                if sale_order_info['status'] == 'canceled':
                                                    if exist:
                                                        exist.action_cancel()
                                            elif exist_invoice.state == 'cancel':
                                                if sale_order_info['status'] == 'pending' or \
                                                                sale_order_info[
                                                                    'status'] == 'pending_payment' or \
                                                                sale_order_info[
                                                                    'status'] == 'processing' or \
                                                                sale_order_info[
                                                                    'status'] == 'icecore_open' or \
                                                                sale_order_info[
                                                                    'status'] == 'onhold':
                                                    exist_invoice.action_invoice_draft()
                                                    exist_invoice.action_invoice_open()
                                                    exist_invoice.compute_taxes()
                                                elif sale_order_info['status'] == 'complete' or \
                                                                sale_order_info[
                                                                    'status'] == 'icecore_ok':
                                                    exist_invoice.action_invoice_draft()
                                                    exist_invoice.compute_taxes()
                                                    self.register_payment(exist_invoice,
                                                                          sale_order_info)
                                            if exist.state != 'sale' and exist.state != 'done' and exist.state != 'cancel':
                                                if sale_order_info['status'] == 'canceled':
                                                    if exist:
                                                        exist.action_cancel()
                                            elif exist.state == 'sale':
                                                if sale_order_info['status'] == 'canceled':
                                                    if exist:
                                                        exist.action_cancel()
                                            elif exist.state == 'done':
                                                if sale_order_info['status'] == 'canceled':
                                                    if exist:
                                                        exist.action_cancel()

                                        self.log(LOGLEVEL.info, 'sale order',
                                                 "Created or changed invoice")

                            self.env.cr.commit()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    self.log(LOGLEVEL.error, 'sale order problem',
                             "Something went wrong with order id " +
                             order['increment_id'] + " with error: " + format(
                                 (exc_type, fname, exc_tb.tb_lineno, str(e))))
                finally:
                    print "all went okay"
        except Exception as e:
            self.log(LOGLEVEL.error, 'sale order problem',
                     "Something went wrong with the orders with error: " + format(e))
        finally:
            self.log(LOGLEVEL.info, 'sale order', "Finished with sale order")

    def get_partners(self, sale_order_info, session, socket):
        # self = self.db_cursor_check()
        vals = {}
        partner_id = False
        # if sale_order_info['customer_email']
        try:
            if 'billing_address' in sale_order_info and 'company' in sale_order_info[
                'billing_address'] and sale_order_info['billing_address']['company'] is not None:
                # its a company, so check/create company and then add the right partners to it
                company_partner_id = self.check_company(sale_order_info['billing_address'], False,
                                                        session, socket)
                if company_partner_id.ids and len(company_partner_id.ids) > 1:
                    company_partner_id = company_partner_id[0]
                address_vals = {}
                partner_id = False
                if 'customer_id' in sale_order_info and sale_order_info['customer_id']:
                    partner_id = self.one_customer_magento(sale_order_info['customer_id'],
                                                           company_partner_id)
                    if partner_id and partner_id.ids and len(partner_id.ids) > 1:
                        partner_id = partner_id[0]
                is_guest = False
                if sale_order_info['customer_is_guest'] == str(1):
                    partner_id = self.env['res.partner'].search(
                        ['&', ('email', '=', str(sale_order_info['customer_email'])),
                         ('type', '=', 'contact'), ('is_company', '!=', True),
                         ('company_id.id', '=', self.magento_web_shop_ids.company.id)])
                    if partner_id and partner_id.ids and len(partner_id.ids) > 1:
                        partner_id = partner_id[0]
                    is_guest = 'guest'
                if not partner_id:
                    if 'billing_address' in sale_order_info:
                        address_vals['type'] = 'contact'
                        address_vals['parent_id'] = company_partner_id.id
                        partner_id = self.create_address(sale_order_info['billing_address'], False,
                                                         is_guest, session, socket, address_vals)
                    elif 'shipping_address' in sale_order_info:
                        address_vals['type'] = 'contact'
                        address_vals['parent_id'] = company_partner_id.id
                        partner_id = self.create_address(sale_order_info['shipping_address'], False,
                                                         is_guest, session, socket, address_vals)
                if 'billing_address' in sale_order_info:
                    address_vals = {'type': 'invoice',
                                    'parent_id': company_partner_id.id}
                    billing_exists = self.env['res.partner'].search(
                        ['&', ('type', '=', address_vals['type']),
                         ('email', '=', sale_order_info['billing_address']['email']),
                         ('company_id.id', '=', self.magento_web_shop_ids.company.id)])
                    if not billing_exists:
                        billing_exists = False
                    if billing_exists and len(billing_exists.ids) > 1:
                        billing_exists = billing_exists[0]
                    billing_address_id = self.create_address(sale_order_info['billing_address'],
                                                             billing_exists, is_guest, session,
                                                             socket, address_vals)
                    vals['partner_invoice_id'] = int(billing_address_id.id)
                if 'shipping_address' in sale_order_info:
                    if 'email' not in sale_order_info['shipping_address'] or \
                                    sale_order_info['shipping_address']['email'] is None:
                        sale_order_info['shipping_address']['email'] = partner_id.email
                    address_vals = {'type': 'delivery',
                                    'parent_id': company_partner_id.id}
                    shipping_exists = self.env['res.partner'].search(
                        ['&', ('type', '=', address_vals['type']),
                         ('email', '=', sale_order_info['shipping_address']['email'])])
                    if not shipping_exists:
                        shipping_exists = False
                    if shipping_exists and len(shipping_exists.ids) > 1:
                        shipping_exists = shipping_exists[0]
                    shipping_address_id = self.create_address(sale_order_info['shipping_address'],
                                                              shipping_exists, is_guest, session,
                                                              socket, address_vals)
                    vals['partner_shipping_id'] = int(shipping_address_id.id)
                vals['partner_id'] = int(partner_id.id)
                return vals
            else:
                # create partners without company
                address_vals = {}
                if 'customer_email' in sale_order_info and sale_order_info[
                    'customer_email'] is not None:
                    address_vals['email'] = sale_order_info['customer_email']
                is_guest = False
                if sale_order_info['customer_is_guest'] == str(1) or sale_order_info[
                    'customer_is_guest'] == None:
                    partner_id = self.env['res.partner'].search(
                        ['&', ('email', '=', str(sale_order_info['customer_email'])),
                         ('type', '=', 'contact'),
                         ('company_id.id', '=', self.magento_web_shop_ids.company.id)])
                    if partner_id and partner_id.ids and len(partner_id.ids) > 1:
                        partner_id = partner_id[0]
                    is_guest = 'guest'
                if not partner_id and 'customer_id' in sale_order_info and sale_order_info[
                    'customer_id']:
                    partner_id = self.one_customer_magento(sale_order_info['customer_id'])
                    if partner_id and partner_id.ids and len(partner_id.ids) > 1:
                        partner_id = partner_id[0]
                if not partner_id:
                    if 'billing_address' in sale_order_info:
                        address_vals['type'] = 'contact'
                        partner_id = self.create_address(sale_order_info['billing_address'], False,
                                                         is_guest, session, socket, address_vals)
                        if partner_id and partner_id.ids and len(partner_id.ids) > 1:
                            partner_id = partner_id[0]
                    elif 'shipping_address' in sale_order_info:
                        address_vals['type'] = 'contact'
                        partner_id = self.create_address(sale_order_info['shipping_address'], False,
                                                         is_guest, session, socket, address_vals)
                        if partner_id and partner_id.ids and len(partner_id.ids) > 1:
                            partner_id = partner_id[0]
                if 'billing_address' in sale_order_info:
                    address_vals = {'type': 'invoice', 'parent_id': partner_id.id}
                    if 'customer_email' in sale_order_info and sale_order_info[
                        'customer_email'] is not None:
                        address_vals['email'] = sale_order_info['customer_email']
                    if not is_guest:
                        magento_id = partner_id.magento_id
                    else:
                        magento_id = - int(sale_order_info['billing_address']['address_id'])

                    billing_exists = self.env['res.partner'].search(
                        ['&', ('type', '=', address_vals['type']), ('magento_id', '=', magento_id),
                         ('company_id.id', '=', self.magento_web_shop_ids.company.id)])
                    if not billing_exists:
                        billing_exists = False
                    if billing_exists and len(billing_exists.ids) > 1:
                        billing_exists = billing_exists[0]
                    billing_address_id = self.create_address(sale_order_info['billing_address'],
                                                             billing_exists, is_guest, session,
                                                             socket, address_vals)
                    if billing_address_id and len(billing_address_id.ids) > 1:
                        billing_address_id = billing_address_id[0]
                    vals['partner_invoice_id'] = int(billing_address_id.id)
                if 'shipping_address' in sale_order_info:
                    address_vals = {'type': 'delivery', 'parent_id': partner_id.id}
                    if 'customer_email' in sale_order_info and sale_order_info[
                        'customer_email'] is not None:
                        address_vals['email'] = sale_order_info['customer_email']
                    shipping_exists = self.env['res.partner'].search(
                        ['&', ('type', '=', address_vals['type']), ('magento_id', '=', - int(
                            sale_order_info['shipping_address']['address_id'])),
                         ('company_id.id', '=', self.magento_web_shop_ids.company.id)])
                    if not shipping_exists:
                        shipping_exists = False
                    if shipping_exists and len(shipping_exists.ids) > 1:
                        shipping_exists = shipping_exists[0]
                    shipping_address_id = self.create_address(sale_order_info['shipping_address'],
                                                              shipping_exists, is_guest, session,
                                                              socket, address_vals)
                    if shipping_address_id and len(shipping_address_id.ids) > 1:
                        shipping_address_id = shipping_address_id[0]
                    vals['partner_shipping_id'] = int(shipping_address_id.id)
                vals['partner_id'] = int(partner_id.id)
                return vals
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            self.log(LOGLEVEL.error, 'partner', "Something went wrong with partner " +
                     str(partner_id) + " with error: " + format(
                (exc_type, fname, exc_tb.tb_lineno, str(e))))

    def one_customer_magento(self, customer_id, company_id=None):
        try:
            socket, session = self.connection()
            exist = False
            vals = {}
            company_id_id = -1
            customer = socket.call(session, "customer.info", [customer_id])
            if 'default_billing' in customer and customer['default_billing'] is not None:
                address = socket.call(session, "customer_address.info",
                                      [customer['default_billing']])
            else:
                address = customer
            if 'email' not in address and 'email' in customer:
                address['email'] = customer['email']
            if company_id is not None and company_id.id:
                company_id_id = company_id.id
                vals['parent_id'] = company_id.id
            if 'customer_address_id' in address and address['customer_address_id'] is not None:
                partner_id = self.env['res.partner'].search(
                    ['&', ('magento_id', '=', str(address['customer_address_id'])),
                     ('type', '=', 'contact'), ('id', '!=', company_id_id),
                     ('company_id.id', '=', self.magento_web_shop_ids.company.id)]).sorted(
                    key=lambda r: r.id)
                if partner_id and partner_id.ids:
                    if len(partner_id.ids) > 1:
                        partner_id = partner_id[0]
                    # if 'parent_id' in vals and vals['parent_id'] != partner_id.id:  # todo: in dit wel nodig?
                    exist = partner_id
            return self.create_address(address, exist, "company_partner", session, socket, vals)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            self.log(LOGLEVEL.error, 'partner',
                     "Something went wrong with partner with error: " + format(
                         (exc_type, fname, exc_tb.tb_lineno, str(e))))

    def check_company(self, address, partner_type, session, socket):
        exist = False
        magento_id = address['customer_address_id']
        if not magento_id or (magento_id and magento_id == '0'):
            magento_id = - int(address['address_id'])
        company_exist = self.env['res.partner'].search(
            ['&', ('magento_id', '=', magento_id), ('is_company', '=', True),
             ('company_id.id', '=', self.magento_web_shop_ids.company.id)])
        if not company_exist:
            vals = {'is_company': True, 'company_type': 'company', 'name': address['company'],
                    'magento_id': magento_id}
            return self.create_address(address, exist, partner_type, session, socket, vals)
        return company_exist

    def create_address(self, address, exist, partner_type, session, socket, vals=None):
        if vals is None:
            vals = {}
        vals['company_id'] = self.magento_web_shop_ids.company.id
        if 'customer_address_id' in address and address['customer_address_id'] is not None:
            vals['magento_id'] = address['customer_address_id']
        elif 'address_id' in address and address['address_id'] is not None:
            vals['magento_id'] = - int(address['address_id'])
        if partner_type == 'guest':
            vals['magento_id'] = - int(address['address_id'])
        if 'fax' in address and address['fax'] is not None:
            vals['fax'] = address['fax']
        if 'postcode' in address and address['postcode'] is not None:
            vals['zip'] = address['postcode']
        if 'city' in address and address['city'] is not None:
            vals['city'] = address['city']
        if 'street' in address and address['street'] is not None:
            vals['street'] = address['street']
            if 'suffix' in address and address['suffix'] is not None:
                vals['street'] += address['suffix']
        if 'telephone' in address and address['telephone'] is not None:
            vals['phone'] = address['telephone']
        if 'email' in address and address['email'] is not None:
            vals['email'] = address['email']
        if 'name' not in vals and 'firstname' in address and address['firstname'] is not None:
            vals['name'] = address['firstname'] + " " + address['lastname']
        if 'taxvat' in address and address['taxvat'] is not None:
            vals['vat'] = self.check_vat(address['taxvat'])
        if 'vat_id' in address and address['vat_id'] is not None:
            vals['vat'] = self.check_vat(address['vat_id'])
        if 'website_id' in address and address['website_id'] is not None:
            vals['website_id'] = address['website_id']
        if 'firstname' in address and address['firstname'] is not None:
            vals['mfirstname'] = address['firstname']
        if 'lastname' in address and address['lastname'] is not None:
            vals['mlastname'] = address['lastname']
        if 'password' in address and address['password'] is not None:
            vals['mpassword'] = address['password']
        if 'gender' in address and address['gender'] is not None:
            vals['mgender'] = int(address['gender'])
        if 'middlename' in address and address['middlename'] is not None:
            vals['mmiddlename'] = address['middlename']
        if 'group_id' in address:
            group_id = self.env['magento.customers.group'].search(
                [('magento_group_id', '=', int(address['group_id']))])
            if group_id:
                vals['magento_group'] = int(group_id.id)
        if 'store_id' in address:
            store = self.env['magento.store'].search(
                [('magento_id', '=', int(address['store_id']))])
            if store:
                vals['store_id'] = store.id
        if address and 'country_id' in address and address['country_id'] is not None:
            country_list = socket.call(session, "directory_country.list")
            for country in country_list:
                if country['country_id'] == address['country_id']:
                    country_id = self.env['res.country'].search(
                        [('code', '=', country['iso2_code'])])
                    if country_id:
                        vals['country_id'] = int(country_id.id)
                        country_id.write({'magento_id': str(country['country_id'])})
            region_list = socket.call(session, "directory_region.list", [address['country_id']])
            for region in region_list:
                if region['region_id'] == address['region_id']:
                    state_id = self.env['res.country.state'].search([('code', '=', region['code'])])
                    if state_id:
                        vals['state_id'] = int(state_id[0].id)
                        state_id[0].write({'magento_id': str(region['region_id'])})
        if 'is_company' in vals and vals['is_company']:
            magento_id = vals['magento_id']
            vals['magento_company_id'] = magento_id
        if not exist:
            return self.env['res.partner'].create(vals)
        else:
            exist.write(vals)
            return exist

    def check_vat(self, vat):
        if vat:
            partner_obj = self.env['res.partner']
            check_func = partner_obj.simple_vat_check
            vat_country, vat_number = partner_obj._split_vat(vat)
            if not check_func(vat_country, vat_number):
                self.log(LOGLEVEL.warning, 'Partner Check',
                         "Importing VAT Number [%s] is not valid !" % vat)
                return False
            return vat
        else:
            return False

    def register_payment(self, invoice, sale_order_info):
        journal = self.get_journal(sale_order_info['payment'])
        if journal and journal.id:
            invoice.pay_and_reconcile(journal)

    def get_journal(self, payment_info):
        socket, session = self.connection()

        if payment_info and payment_info['method']:
            journal = self.env['account.journal'].search(
                ['&', ('magento_code', '=', payment_info['method']),
                 ('company_id.id', '=', self.magento_web_shop_ids.company.id)])
            if not journal:
                possible_payment_methods = False
                if 'quote_id' in payment_info and payment_info['quote_id'] is not None:
                    try:
                        possible_payment_methods = socket.call(session, "cart_payment.list",
                                                               [payment_info['quote_id']])
                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self.log(LOGLEVEL.warning, 'sale order',
                                 "Possible problem: no or wrong journal. \n"
                                 "Something went wrong with getting quote id of payment: " + format(
                                     (exc_type, fname, exc_tb.tb_lineno, str(e))))
                elif 'quote_payment_id' in payment_info and payment_info[
                    'quote_payment_id'] is not None:
                    possible_payment_methods = socket.call(session, "cart_payment.list",
                                                           [payment_info['quote_payment_id']])
                if possible_payment_methods:
                    for possible_payment_method in possible_payment_methods:
                        if payment_info['method'] == possible_payment_method['code']:
                            journal_object = self.env['account.journal']
                            journal = journal_object.create({'name': str(possible_payment_method[
                                                                             'title'] + " (" + self.magento_web_shop_ids.company.name + ")"),
                                                             'company_id': self.magento_web_shop_ids.company.id,
                                                             'code': possible_payment_method[
                                                                         'code'][
                                                                     -5:],
                                                             'type': 'bank',
                                                             'magento_code':
                                                                 possible_payment_method[
                                                                     'code']
                                                             })
            if journal.id:
                return journal
            else:
                return False

    def process_invoice_list(self, invoice_list, magento_settings, socket,
                             session):  # probably not used
        new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        uid, context = self.env.uid, self.env.context
        with api.Environment.manage():
            new_cr.autocommit(True)
            self = self.with_env(self.env(cr=new_cr)).with_context(original_cr=self._cr)

            try:
                for invoice in invoice_list:
                    invoice_info = socket.call(session, "sales_order_invoice.info",
                                               [invoice['increment_id']])
                    order_info = socket.call(session, "sales_order.info",
                                             [invoice_info['order_increment_id']])
                    vals_invoice = {}
                    partner_id = False
                    sale_order = self.env['sale.order'].search(
                        [('magento_id', '=', order_info['increment_id'])])

                    vals_invoice['magento_id'] = str(invoice['increment_id'])
                    exist_invoice = self.env['account.invoice'].search(
                        [('magento_id', '=', str(vals_invoice['magento_id']))])
                    if order_info and 'customer_id' in order_info:
                        if order_info['customer_id'] != None:
                            partner_id = self.env['res.partner'].search(
                                ['&', ('magento_id', '=', int(order_info['customer_id'])),
                                 ('company_id.id', '=', self.magento_web_shop_ids.company.id)])
                            if len(partner_id.ids) > 1:
                                tmp_partner = partner_id[0]
                                for partner in partner_id:
                                    if partner.parent_id.id:
                                        tmp_partner = partner
                                partner_id = tmp_partner
                        if not partner_id:
                            partner_id = self.env['res.partner'].search(
                                [('name', '=', 'Guest')])
                            if not partner_id:
                                partner_id = self.env['res.partner'].create({'name': 'Guest'})
                        if 'increment_id' in order_info:
                            vals_invoice['origin'] = str(order_info['increment_id'])
                        if partner_id:
                            if len(partner_id.ids) > 1:
                                print "partners are stupid"
                            lines_invoice = []
                            vals_invoice['partner_id'] = int(partner_id.id)
                            if not exist_invoice:
                                for item in invoice_info['items']:
                                    product_id = self.env['product.product'].search(
                                        [('magento_id', '=', int(item['product_id']))])
                                    if product_id:
                                        product_id = product_id[0]
                                        for sale_order_line in sale_order:
                                            if product_id == sale_order_line.product_id:
                                                lines_invoice.append(
                                                    (0, 0,
                                                     {'product_id': int(product_id.id),
                                                      'uom_id': int(product_id.uom_id.id),
                                                      'name': item['name'],
                                                      'quantity': float(item['qty']),
                                                      'account_id': int(
                                                          magento_settings.magento_account_id.id),
                                                      'price_unit': float(item['price']),
                                                      'sale_line_ids': (
                                                          6, 0, [sale_order_line.id])}))
                            else:
                                for invoice_line in invoice_info['items']:
                                    for existing_invoice_line in exist_invoice.invoice_line_ids:
                                        if str(existing_invoice_line.product_id.magento_id) == \
                                                invoice_line['product_id']:
                                            for sale_order_line in sale_order.order_line:
                                                if existing_invoice_line.product_id == sale_order_line.product_id:
                                                    existing_invoice_line.uom_id = existing_invoice_line.product_id.uom_id.id
                                                    existing_invoice_line.write({'sale_line_ids': [
                                                        (6, 0, sale_order_line.ids)]})
                                                    # todo: lines invoice speciaal maken als al bestaat, eigenlijk de regels dus aanpassen
                            new_line = []
                            clean_line = []
                            clean_line.append((5,))
                            new_line.extend(clean_line)
                            new_line.extend(lines_invoice)
                            if 'state' in invoice_info:
                                if invoice_info['state'] != '2':
                                    vals_invoice['invoice_line_ids'] = new_line
                            if 'created_at' in invoice_info:
                                vals_invoice['date_invoice'] = invoice_info['created_at']

                            vals_invoice['name'] = invoice['increment_id']
                            vals_invoice['number'] = invoice['increment_id']

                            if magento_settings:
                                vals_invoice['account_id'] = int(
                                    magento_settings.magento_account_id.id)
                                vals_invoice['company_id'] = int(
                                    magento_settings.magento_company_id.id)
                                vals_invoice['currency_id'] = int(
                                    magento_settings.magento_currency_id.id)
                                vals_invoice['journal_id'] = int(
                                    magento_settings.magento_journal_id.id)

                            if not exist_invoice:
                                vals_invoice['state'] = 'draft'

                                vals_invoice['invoice_line_ids'] = lines_invoice
                                new_invoice = self.env['account.invoice'].create(vals_invoice)
                                # sale_order.invoice_ids.id = new_invoice.id
                                sale_order.write({'invoice_ids': [(4, new_invoice.id)]})
                                if new_invoice.invoice_line_ids.ids:
                                    if 'state' in invoice_info:
                                        if invoice_info['state'] == '1':
                                            new_invoice.action_invoice_open()
                                        if invoice_info['state'] == '2':
                                            new_invoice.action_invoice_open()
                                            new_invoice.action_move_create()
                                            new_invoice.action_invoice_paid()
                                        if invoice_info['state'] == '3':
                                            new_invoice.action_invoice_open()
                                            new_invoice.action_invoice_cancel()
                                        self.log(LOGLEVEL.info, 'Sale Order',
                                                 'Created invoice: ' + invoice['increment_id'])
                            else:
                                exist_invoice.write(vals_invoice)
                                sale_order.write({'invoice_ids': [(6, 0, [exist_invoice.id])]})
                                self.log(LOGLEVEL.info, 'Sale Order',
                                         'Modification of invoice: ' + invoice['increment_id'])
                            self.env.cr.commit()
            finally:
                self.log(LOGLEVEL.info, 'Sale Order', 'finished with orders')

    def sync_single_sale_order(self, magento_increment_id):
        filters = {'increment_id': str(magento_increment_id)}
        self.log(LOGLEVEL.info, 'Single sale order', "started single sale order import")
        big_list = []
        self.log(LOGLEVEL.info, 'Single sale order',
                 'started cron incremental sale orders with filters with filters: ' + str(filters))
        socket, session = self.connection()
        sale_order_list = socket.call(session, "sales_order.list", [filters])
        big_list.extend(sale_order_list)
        split_list = []
        split_list.append(big_list)

        if len(split_list) == 1 and len(big_list) == 0:
            self.log(LOGLEVEL.info, 'Single sale order',
                     'Ended Single sale order update: 0 sale orders to create/update')
        else:
            self.log(LOGLEVEL.info, 'Single sale order',
                     'Found ' + str(len(big_list)) + ' sale orders to create/update')
        for list in split_list:
            self.process_simple_order(list)
        print "done"
