# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2015 ICTSTUDIO (www.ictstudio.eu).
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

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ExternalFulfilmentPartner(models.Model):
    _name = 'external.fulfilment.partner'
    _description = "External Fulfilment Partner"
    _rec_name='external_fulfilment'


    partner = fields.Many2one(
            comodel_name='res.partner',
            string='Partner'
    )
    external_fulfilment = fields.Many2one(
            comodel_name="external.fulfilment",
            required=True
    )
    active = fields.Boolean(
            string="Active",
            default=True
    )
    description = fields.Text(
            string="Description"
    )
    external_id = fields.Char(
            string="External Identifier"
    )
    sales_team_id = fields.Many2one(
            comodel_name='crm.team',
            string='Sales Team'
    )

    @api.model
    def check_order_state(self):
        """
        Check the order state of all fulfil partners one by one
        :return:
        """
        fulfil_partners = self.search([('active', '=', True)])
        for fp in fulfil_partners:
            _logger.debug('FP Orderlist State: %s', fp)
            fp.fulfil_orderlist_state()
        return True

    @api.multi
    def fulfil_orderlist_state(self):
        """
        Hook to provide orderlist_state
        :return:
        """
        self.ensure_one()
        _logger.debug('Orderlist State Base Hook')
        return False

    @api.model
    def check_product_sync(self):
        fulfil_partners = self.search([('active', '=', True)])
        for fp in fulfil_partners:
            _logger.debug('Product Sync: %s', fp)
            fp.fulfil_product_sync()
        return True

    @api.multi
    def fulfil_product_sync(self):
        """
        Hook to provide productlist
        :return:
        """
        self.ensure_one()
        _logger.debug('Product Sync')
        return False

    @api.model
    def prepare_external_order_list(self):
        orderlist = []
        self.ensure_one()

        pos = self.env['purchase.order'].search(
                [
                    ('external_fulfilment_partner', '=', self.id),
                    ('external_state', 'in', ['processing', 'new'])
                ]
        )

        for po in pos:
            orderlist.append(
                    {'ref': po.external_id}
            )
        return orderlist and {
            'orderlist': orderlist,
            'CustomerRef': self.external_id
        } or False

    @api.model
    def process_order_state(self, order_line_values):
        values = order_line_values.get('order')
        if values and values.get('ref'):
            pos = self.env['purchase.order'].search(
                    [
                        ('external_fulfilment_partner', '=', self.id),
                        ('external_id' , '=', values.get('ref'))
                    ]
            )
            for po in pos:
                if po.external_state != values.get('state'):
                    po.external_state = values.get('state')
                    if values.get('state') == 'shipped':
                        for picking in po.picking_ids:
                            _logger.debug("Process Picking: %s", picking.name)
                            picking.action_done()

    @api.model
    def fulfil_product_sync_confirm(self, list):
        """
        Hook to provide product sync confirm
        :return:
        """
        _logger.debug('Product Sync Confirm')
        return False

    @api.model
    def process_product(self, ext_product):
        product = self.env['external.productsync']._get_product_by_suppliersku(
                ext_product.get('sku'),
                self.partner
        )

        _logger.debug(
                'Process Product: %s %s %s',
                ext_product,
                ext_product.get('sku'),
                product
        )
        if product:
            product.write(
                    {
                        'external_fulfilment_qty': ext_product.get('qty'),
                        'external_fulfilment_eol': ext_product.get('eol'),
                        'standard_price': ext_product.get('price')
                    }
            )

            _logger.debug('Update Product: %s %s', product.name, ext_product)
        return ext_product.get('feedbackid')

    @api.multi
    def fulfil_product_map(self):
        self.ensure_one()
        return self.get_fulfil_product_list()

    @api.multi
    def get_fulfil_product_list(self):
        """
        Provide a list of products with the current FulFil Partner
        :return:
        """
        self.ensure_one()
        values = {
            'CustomerRef': self.external_id,
            'productlist':[]
        }

        productlist = self.env['product.product'].search(
                [
                    ('seller_id', '=', self.partner.id),
                    ('type', '=', 'product')
                ]
        )
        for product in productlist:
            product_sku = self.env['external.productsync']._get_external_product_code(
                    product,
                    self.partner
            )

            product_info = {'product': {'sku': product_sku}}
            values['productlist'].append(product_info)

        _logger.debug("List of products %s", values)
        return values