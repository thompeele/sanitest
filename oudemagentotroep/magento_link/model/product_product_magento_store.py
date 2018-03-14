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

from datetime import date, timedelta
import logging
from odoo import fields, models, api


_logger = logging.getLogger(__name__)


class product_product_magento_store(models.Model):
    _name = "product.product.magento.store"
    _description = "Product Magento Store Specific"

    @api.multi
    def _current_price(self):
        res = {}

        current_datetime = date.today()
        current_date = self._context.get('date') or current_datetime.strftime('%Y-%m-%d')

        for line in self:
            new_price = 0.0
            if line.special_price and ((line.special_from is False) or (line.special_from <= current_date)) and ((line.special_to is False) or (line.special_to >= current_date)):
                new_price = line.special_price
            elif line.price:
                new_price = line.price

            res[line.id] = new_price
        return res

    product_name = fields.Char('Name')
    description_short = fields.Text('Short Description')
    description = fields.Text('Description')
    product_id = fields.Many2one("product.product", "Product", required=True)
    store_id = fields.Many2one("magento.store", "Magento Store", required=True)
    special_price = fields.Float(string="Special Price")
    special_from = fields.Date(string="Special Price From")
    special_to = fields.Date(string="Special Price To")
    price = fields.Float(string="Price")
    meta_title = fields.Char(string="Meta Title", size=256)
    meta_keyword = fields.Char(string="Meta Keyword", size=256)
    meta_description = fields.Char(string="Meta Description", size=256)
    new_from = fields.Date(string="New From")
    new_to = fields.Date(string="New To")
    url_key = fields.Char(string="URL key", size=256)
    url_path = fields.Char(string="URL path", size=256)
    public_price = fields.Float(string="Public Price (MSRP)")
    pp_enabled = fields.Integer(string="Public Price Enabled")
    pp_disp_act_price_type = fields.Integer(string="Public Price Display Actual Price Type")
    custom_design = fields.Float(string="Custom Design")
    custom_design_from = fields.Date(string="Custom Design From")
    custom_design_to = fields.Date(string="Custom Design To")
    current_price = fields.Float(compute='_current_price',
                                 string='Current Price')

    _sql_constraints = [
        ("product_store_unique", "unique (product_id, store_id)",
         "You can only define a store 1 time for each product")
    ]

    @api.multi
    def write(self, values):
        retval = super(product_product_magento_store, self).write(values)
        self.pricelist_store_update()
        return retval

    @api.model
    def create(self, values):
        ret_id = super(product_product_magento_store, self).create(
            values
        )
        ret_id.pricelist_store_update()
        return ret_id

    @api.multi
    def unlink(self):
        self.pricelist_store_unlink()
        retval = super(product_product_magento_store, self).unlink()
        return retval

    @api.multi
    def pricelist_store_unlink(self):

        current_datetime = date.today()
        current_date = self._context.get('date') or current_datetime.strftime('%Y-%m-%d')

        for line in self:
            pricelist = line.store_id.pricelist_id
            version = False
            for v in pricelist.version_id:
                if ((v.date_start is False) or (v.date_start <= current_date)) and ((v.date_end is False) or (v.date_end >= current_date)):
                    version = v
                    break
            if not version:
                _logger.error("No valid pricelist version")
                continue

            item = False
            for i in version.items_id:
                if i.product_id == line.product_id:
                    item = i

            if item:
                self.env['product.pricelist.item'].unlink([item.id])

    @api.multi
    def sync_store_prices(self):
        _logger.debug("Start Product Sync")
        current_datetime = date.today()
        check_datetime = current_datetime - timedelta(days=1)

        current_date = current_datetime.strftime('%Y-%m-%d')
        check_date = check_datetime.strftime('%Y-%m-%d')

        # Search Prices with special start dates set
        from_price_ids = self.search(
            [
                ('special_from', '=', current_date),
            ],
        )
        _logger.debug("From Current Date: %s the IDS: %s", current_date, from_price_ids)
        if from_price_ids:
            from_price_ids.pricelist_store_update()

        # Search Prices with special end dates set
        to_price_ids = self.search([(
            'special_to', '=', check_date)])
        _logger.debug("To Check Date: %s the IDS: %s", check_date, to_price_ids)
        if to_price_ids:
            to_price_ids.pricelist_store_update()

    @api.multi
    def pricelist_store_update(self):
        current_datetime = date.today()
        current_date = self._context.get('date') or current_datetime.strftime('%Y-%m-%d')

        for line in self:
            pricelist = line.store_id.pricelist_id
            version = False
            for v in pricelist.item_ids:
                if ((v.date_start is False) or (v.date_start <= current_date)) and ((v.date_end is False) or (v.date_end >= current_date)):
                    version = v
                    break
            if not version:
                _logger.error("No valid pricelist Items")
                continue

            item = False
            for i in version:
                if i.product_id == line.product_id:
                    item = i

            if item and line.current_price and item.price_surcharge != line.current_price:
                _logger.debug('Update Pricelist: Product: %s (%s)', line.product_id.id, line.current_price)
                self.env['product.pricelist.item'].browse(item.id).write({'base': 1,
                                                                          'price_discount': -1,
                                                                          'price_surcharge': line.current_price})
            elif item and not line.current_price:
                _logger.debug('Unlink Pricelist: Product: %s', line.product_id.id)
                self.env['product.pricelist.item'].unlink([item.id])
            elif not item and line.current_price:
                _logger.debug('Create Pricelist: Product: %s (%s)', line.product_id.id, line.current_price)
                self.env['product.pricelist.item'].create({'base': 1,
                                                           'product_id': line.product_id.id,
                                                           'price_version_id': version.id,
                                                           'price_discount': -1,
                                                           'price_surcharge': line.current_price})
