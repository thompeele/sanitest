# -*- coding: utf-8 -*-
# Copyright© 2016 ICTSTUDIO <http://www.ictstudio.eu>
# License: AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Business2Business(models.Model):
    _name = "business.2.business"
    _description = "Business2Business Base Module"
    _rec_name="partner_id"

    partner_id = fields.Many2one(
            comodel_name='res.partner',
            string='Customer',
            required=True
    )
    pricelist_id = fields.Many2one(
            comodel_name='product.pricelist',
            string='Overrule Partner Pricelist'
    )
    section_id = fields.Many2one(
            comodel_name='crm.team',
            string='Linked Sales Team',
            required=True
    )
    active = fields.Boolean(
        string="Active",
        default=True
    )
    description = fields.Text(
        string="Description"
    )
    confirm_order = fields.Boolean(
        string="Confirm Orders when receiving order"
    )
    lines = fields.One2many(
            comodel_name='business.2.business.line',
            inverse_name='b2b',
            string='Special Lines'
    )

    @api.model
    def _check_values(self, values):
        if values.get('CustomerRef') and values.get('OrderRef'):
            return True
        return False

    @api.model
    def _check_order_values(self, values):
        if self._check_values(values) and values.get('Lines') and len(values.get('Lines'))>0:
            return True
        return False

    @api.model
    def _process_order_values(self, values, partner):
        """
       Inheritable Method to parse the magento values passed to ODOO
       :param cr:
       :param uid:
       :param values: set of magento order values
       :param context:
       :return:
       """
        _logger.debug('B2B Process Order Values: %s', values)
        order_values={}
        order_values['partner_id'] = partner.id
        if values.get('OrderRef'):
            order_values['client_order_ref'] = values.get('OrderRef')
        order_values['section_id'] = self.section_id.id
        order_values['pricelist_id'] = self.partner_id.property_product_pricelist.id or self.pricelist_id.id
        if values.get('Address'):
            dropship_address = self.env['dropship.address'].create_address(values.get('Address'))
            if dropship_address:
                order_values['dropship_address'] = dropship_address.id
        return order_values

    @api.model
    def request_orderlist_state(self, values):
        partner, b2b = self.get_partner_and_b2b(values)
        response = {'orderlist': []}
        if partner and b2b and values.get('orderlist'):
            for order in values.get('orderlist'):
                response['orderlist'].append(self.retreive_order_state(order, partner))
            return response
        else:
            return {'error': {'code': 1, 'message': 'Misconfiguration'}}

    @api.model
    def get_external_order_state(self, order):
        if not order:
            return 'error'
        if order.shipped and not order.invoiced:
            return 'shipped'
        elif order.shipped and order.invoiced:
            return 'shipped'
        else:
            return 'processing'

    @api.model
    def retreive_order_state(self, values, partner):
        if values.get('id'):
            order = self.env['sale.order'].browse(values.get('id'))
        elif values.get('ref'):
            order = self.env['sale.order'].search(
                [
                    ('name', '=', values.get('ref')),
                    ('partner_id', '=', partner.id)
                ]
            )
        if order and len(order)==1:
            return {'order': {'id': order.id, 'ref': order.name, 'state': self.get_external_order_state(order)}}
        else:
            return {'order': {'id': values.get('id'), 'ref': values.get('ref'), 'state': 'error'}}


    @api.model
    def get_partner_and_b2b(self, values):
        b2b = False

        partners = self.env['res.partner'].search(
                [
                    ('ref', '=', values.get('CustomerRef')),
                    ('parent_id', '=', False)
                ]
        )
        if partners and partners[0]:
            b2b = self.search(
                    [
                        ('partner_id','=', partners[0].id)
                    ]
            )
        return partners and partners[0] or False, b2b or False

    @api.model
    def receive_order(self, values):

        if self._check_order_values(values):
            partner, b2b = self.get_partner_and_b2b(values)

            if b2b and len(b2b) == 1:
                #try:
                    """
                    Check if an order exists already with same reference and partner, otherwise create new
                    """
                    _logger.debug('Create B2C Order Values: %s', values)
                    _logger.debug('Create B2C Order partner: %s', partner)
                    orders = self.env['sale.order'].search(
                        [
                            ('client_order_ref', '=', values.get('OrderRef')),
                            ('partner_id', '=', partner.id)
                        ]
                    )
                    if orders and orders[0]:
                        order = orders[0]
                        _logger.debug('Order found, use this one to return %s', order.name)
                    else:
                        _logger.debug('Order not found, create new order')
                        order = b2b._create_order(values, partner)
                    
                    if order:
                        return {'order': {'id': order.id, 'ref':order.name}}
                    else:
                        return {'error': {'code': 2, 'message': 'Error creating order'}}
                #except:
                #    return {'error': {'code': 1, 'message': 'Error creating Order'}}

            else:
                return {'error': {'code': 3, 'message': 'Wrong configured B2B'}}
        else:
            return {'error': {'code': 4, 'message': 'Unaccepted Order Values'}}

        return {'error': {'code': 99, 'message': 'Undefined Error'}}


    @api.model
    def _process_order_line_values(self, receive_values, order):

        _logger.debug('B2B Process Order Line Values: %s', receive_values)
        # Line values are: 'ProductCode', 'Quanity'
        values={}

        products = self.env['product.product'].search(
                [
                    ('default_code', '=', receive_values.get('ProductCode'))
                ]
        )

        if products and products[0]:
            product = products[0]
        else:
            receive_values['order_id'] = order.id
            return receive_values
        receive_values['order_id'] = order.id
        receive_values['product_id'] = product.id
        receive_values['product_uom'] = product.uom_id.id
        receive_values['product_uom_qty'] = receive_values.get('Quantity') or 0

        return receive_values

    @api.model
    def _create_order(self, values, partner):
        order_vals=self._process_order_values(values, partner)
        if order_vals:
            #try:
            order = self.env['sale.order'].create(order_vals)
            if order:
                for line_values in values.get('Lines'):
                    _logger.debug("LineValues: %s", line_values)
                    line_values = self._process_order_line_values(line_values, order)
                    _logger.debug("ProcLineValues: %s", line_values)
                    l = self.env['sale.order.line'].create(line_values)
                    l.product_id_change()
                for line in self.lines:
                    if line.type == 'sale_extra':
                        line_values = line._process_extra_order_line(order)
                        self.env['sale.order.line'].create(line_values)
            if self.confirm_order:
                order.signal_workflow('order_confirm')
            return order
            # #except:
            #     _logger.error("B2B Error creating order from values")
            #     return False


        else:
            return False

    @api.model
    def cancel_order(self, values):
        if self._check_values(values):
            partner, b2b = self.get_partner_and_b2b(values)
            if partner and b2b and len(b2b) == 1:
                order = self.env['sale.order'].search(
                        [
                            ('client_order_ref', '=', values.get('OrderRef')),
                            ('partner_id', '=', partner.id)
                        ]
                )
                if len(order) == 1:
                    try:
                        res = order.action_cancel()
                        if res:
                            return {'order': {'id': order.id, 'ref':order.name}}
                        else:
                            return {'error': {'code': 4, 'message': 'Error Cancelling Order'}}
                    except Exception:
                        return {'error': {'code': 4, 'message': 'Error Cancelling Order'}}
                else:
                    return {'error': {'code': 10, 'message': 'Order is processing'}}
            else:
                return {'error': {'code': 3, 'message': 'Wrong configured B2B'}}
        else:
            return {'error': {'code': 4, 'message': 'Unaccepted Order Values'}}

        return {'error': {'code': 99, 'message': 'Undefined Error'}}
