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
import xmlrpclib
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class product_product(models.Model):
    _inherit = "product.product"

    store_ids = fields.One2many("product.product.magento.store",
                                "product_id",
                                string="Magento Stores")
    meta_title = fields.Char(string="Meta Title", size=256)
    meta_keyword = fields.Char(string="Meta Keyword", size=256)
    meta_description = fields.Char(string="Meta Description", size=256)
    url_key = fields.Char(string="URL key", size=256)
    url_path = fields.Char(string="URL path", size=256)
    new_from = fields.Date(string="New From")
    new_to = fields.Date(string="New To")
    public_price = fields.Float(string="Public Price (MSRP)")
    pp_enabled = fields.Integer(string="Public Price Enabled")
    pp_disp_act_price_type = fields.Integer(string="Public Price Display Actual Price Type")
    custom_design = fields.Float(string="Custom Design")
    custom_design_from = fields.Date(string="Custom Design From")
    custom_design_to = fields.Date(string="Custom Design To")
    special_price = fields.Float(string="Special Price")
    special_from = fields.Date(string="Special Price From")
    special_to = fields.Date(string="Special Price To")
    magento_type = fields.Many2one('magento.product.type', 'Magento Type')
    magento_attribute_set = fields.Many2one("magento.attribute.set",
                                            "Magento Attribute Set")
    magento_image = fields.Char('Magento Image', size=128)
    magento_image_change = fields.Boolean('Magento Image Change')
    magento_visible = fields.Selection([
        (1, "Not Visible"),
        (2, "In Catalog"),
        (3, "In Search"),
        (4, "In Catalog/Search")],
        string='Visible in Magento')
    magento_send = fields.Boolean('Send to Magento')
    short_description = fields.Text('Short Description', translate=True)

    _defaults = {
        'magento_image_change': lambda *a: 1
    }

    @api.multi
    def write(self, vals):
        if vals.get('image') or vals.get('image_variant'):
            vals['magento_image_change'] = True

        return super(product_product, self).write(vals)

    @api.multi
    def sync_stock_quantity(self):

        #If run by cron job the ids will be empty
        if not self._ids:
            self._ids = self.search([])

        if isinstance(self._ids, (long, int)):
            self._ids = [self._ids]

        for id in self._ids:
            response = self.update_stock_quantity(id)

            if response[0] == 1:
                _logger.debug('Updated Stock for Product: %s', (id))
            else:
                map_id = self.env['magento.product'].search([(
                    'pro_name', '=', id)])
                if map_id:
                    self.env['magento.product'].browse(map_id.id).write({'need_sync': 'Yes'})
                self.env['magento.sync.history'].create(
                    {
                        'status': 'no',
                        'action_on': 'product',
                        'action': 'c',
                        'error_message': response[1]
                    }
                )

    @api.multi
    def product_sync_yes(self):
        _logger.debug("IDS: %s", self._ids)
        sync_ids = []
        for product_id in self:
            _logger.debug("Product_id: %s", product_id)
            map_id = self.env['magento.product'].search([(
                'oe_product_id', '=', product_id)])
            _logger.debug("Map_id: %s", map_id.id)
            if map_id and map_id[0] and not map_id[0] in sync_ids:
                _logger.debug("Add Mapping Product: %s", map_id.id)
                sync_ids.append(map_id[0].id)

        if sync_ids:
            _logger.debug("Magento Product Sync Yes: %s", sync_ids)
            self.env['magento.product'].browse(sync_ids).write({'need_sync': 'Yes'})

    @api.multi
    def update_stock_quantity(self):

        _logger.debug('Stock Update for following product(s): %s', (self._ids))

        for product in self:
            session = 0
            text = ''
            stock = 1
            qty = 0
            check_mapping = self.env['magento.product'].search([('pro_name', '=', product.id)])
            _logger.debug('Check Mapping: %s', (check_mapping))
            if check_mapping:
                map_obj = self.env['magento.product'].browse(check_mapping[0].id)
                mage_product_id = map_obj.mag_product_id
                config_id = self.env['magento.configure'].search([('active', '=', True)])
                if not config_id:
                    return [0, 'Connection needs one Active Configuration setting.']
                if len(config_id.id) > 1:
                    return [0, 'Sorry, only one Active Configuration setting is allowed.']
                else:
                    obj = self.env['magento.configure'].browse(config_id[0].id)
                    url = obj.name+'/index.php/api/xmlrpc'
                    user = obj.user
                    pwd = obj.pwd
                    try:
                        server = xmlrpclib.Server(url)
                        session = server.login(user, pwd)
                    except xmlrpclib.Fault, e:
                        text = 'Error, %s Magento Api details are Invalid.' % e
                    except IOError, e:
                        text = 'Error in Api Connection, %s.' % e
                    except Exception, e:
                        text = 'Error in Magento Api Connection, %s.' % e
                    if not session:
                        return [0, text]
                    else:
                        try:
                            current_stock = product.qty_available - product.outgoing_qty
                            if product.mag_temp_unavailable:
                                qty = -10000
                                stock = 1
                            else:
                                qty = current_stock or 0.0
                                stock = 1

                            _logger.debug('Update Magento stock of product: %s', (product.name))

                            server.call(
                                session,
                                'product_stock.update',
                                [mage_product_id,
                                 {
                                     'manage_stock': 1,
                                     'qty': qty,
                                     'is_in_stock': stock
                                 }
                                 ]
                            )
                            return [1, '']

                        except Exception, e:
                            return [0, ' Error in Updating Quantity for Magneto Product Id %s.' % mage_product_id]
            else:
                return [0, 'Error in Updating Stock, OE Product Id %s not found in Mapping table.' % product.id]
