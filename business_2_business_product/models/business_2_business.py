# -*- coding: utf-8 -*-
# Copyright© 2016 ICTSTUDIO <http://www.ictstudio.eu>
# License: AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Business2Business(models.Model):
    _inherit = "business.2.business"

    min_stock_qty = fields.Float(
        string="Min Qty",
        default=0.0
    )
    max_stock_qty = fields.Float(
            string="Max Qty",
            default=100.0
    )

    @api.model
    def get_pricelist(self):
        return self.pricelist_id or self.partner_id.property_product_pricelist

    @api.model
    def get_product_price(self, product, pricelist):
        return pricelist.price_get(product.id, 1)[pricelist.id] or product.list_price

    @api.model
    def get_product_stock(self, product):
        current_stock = product.qty_available - product.outgoing_qty
        if current_stock <= self.min_stock_qty:
            current_stock = 0.0
        elif current_stock >= self.max_stock_qty:
            current_stock = self.max_stock_qty
        elif not current_stock:
            current_stock = 0.0
        return current_stock

    @api.model
    def get_product_data(self, product, pricelist):
        current_stock = self.get_product_stock(product)
        end_of_life = not product.purchase_ok
        final_price = self.get_product_price(product, pricelist)

        values = {
            'sku': product.barcode,
            'qty': current_stock,
            'price': final_price,
            'eol': end_of_life,
        }

        return values

    @api.model
    def check_product(self, product):
        if product.type == 'product':
            return True
        if product.type == 'consu':
            return True
        return False

    @api.model
    def get_need_sync_connection(self):
        need_sync_connections = self.env['need.sync.connection'].search([])
        return need_sync_connections.filtered(lambda nsc: nsc.connection == self)

    @api.model
    def request_product_data(self, values):
        _logger.debug('Received values %s', values)
        partner, b2b = self.get_partner_and_b2b(values)
        _logger.debug('Request Productlist for %s (%s) %s', b2b, partner, b2b.id)
        response = {'productlist': []}

        if not b2b or not partner:
            _logger.error("No B2B or Partner Found")
            return response

        need_sync_connection = b2b.get_need_sync_connection()
        if need_sync_connection:
            needsynclist = need_sync_connection.get_need_sync_list('product.product')
        else:
            _logger.error("No Need Sync Connection Linked")
            return response
        _logger.debug('Productlist Selected %s', needsynclist)

        pricelist = b2b.get_pricelist()
        _logger.debug('Pricelist %s', pricelist)

        if not pricelist:
            #TODO: Add errors to product list message for now return empty list and log an error
            _logger.error("No Correct Pricelist Defined on Partner or B2B object")
            return response

        need_sync_lines_invalid = self.env['need.sync.line']
        for needsyncproduct in needsynclist:
            product = needsyncproduct.record
            if product and b2b.check_product(product):
                product_values = b2b.get_product_data(product, pricelist)
                product_values.update({'feedbackid':needsyncproduct.id})
                product_info = {'product': product_values}
                response['productlist'].append(product_info)
                _logger.debug('Productinfo %s', product_info)
            else:
                need_sync_lines_invalid = need_sync_lines_invalid | needsyncproduct

        # Not a Valid Need Sync Line for this Connection
        if need_sync_lines_invalid:
            need_sync_lines_invalid.write({'last_sync_date': fields.Datetime.now()})

        return response

    @api.model
    def map_product_data(self, values):
        partner, b2b = self.get_partner_and_b2b(values)

        if not b2b or not partner:
            _logger.error("No B2B or Partner Found")
            return False
        need_sync_connection = b2b.get_need_sync_connection()
        _logger.debug('Map SKU List from %s (%s) %s', b2b, partner, b2b.id)
        if values.get('productlist'):
            productlist = values.get('productlist')
            list_products=[]
            for product in productlist:

                sku = product['product']['sku']
                _logger.debug("Product %s", sku)
                search_product = self.env['product.product'].search(
                    [
                        ('barcode', '=', sku)
                    ]
                )

                if search_product and search_product[0]:
                    list_products.append(search_product[0].id)
            need_sync_connection.map_need_sync('product.product', list_products)
        return True

    @api.model
    def confirmsync(self, syncvalueids):
        _logger.debug("Trying to Confirm sync ids %s", syncvalueids)
        lines = self.env['need.sync.line'].browse(syncvalueids)
        lines.write({'last_sync_date': fields.Datetime.now()})
        _logger.debug("Success confirmed sync ids %s", syncvalueids)
        return True