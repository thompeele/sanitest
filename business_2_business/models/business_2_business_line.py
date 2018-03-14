# -*- coding: utf-8 -*-
# Copyright© 2016 ICTSTUDIO <http://www.ictstudio.eu>
# License: AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class Business2BusinessLine(models.Model):
    _name = "business.2.business.line"
    _description = "Business2Business Lines"

    def _select_type(self):
        return [
            ('sale_extra', 'Sale Order Extra Cost'),
            ('retour_extra', 'Retour Extra Cost'),
        ]

    type = fields.Selection(
        selection=_select_type)
    product_id = fields.Many2one(
            comodel_name='product.product',
            string='Product',
            required=True)
    price_unit = fields.Float(
            string='Unit Price')
    b2b = fields.Many2one(
            comodel_name='business.2.business',
            string='B2B'
    )

    @api.model
    def _process_extra_order_line(self, order):

        # Line values are: 'ProductCode', 'Quanity'
        values = {
            'order_id': order.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_id.id,
            'product_uom_qty': 1
        }

        defaults = self.pool.get(
                'sale.order.line').product_id_change(
                self._cr,
                self._uid,
                [],
                order.pricelist_id.id,
                values['product_id'],
                qty=float(values.get('product_uom_qty', False)),
                uom=values.get('product_uom', False),
                qty_uos=float(values.get('product_uos_qty', False)),
                uos=values.get('product_uos', False),
                name=values.get('name', False),
                partner_id=order.partner_id.id,
                date_order=order.date_order,
                fiscal_position=order.fiscal_position.id if order.fiscal_position else False,
                flag=False,  # Force name update
                context=self._context
                )['value']
        _logger.debug("B2B Extra Order Line defaults: %s", defaults)

        if defaults.get('tax_id'):
            values['tax_id'] = [(6, 0, defaults['tax_id'])]
        if not self.price_unit and defaults.get('price_unit'):
            values['price_unit'] = defaults.get('price_unit')
        else:
            values['price_unit'] = self.price_unit
        if defaults.get('name'):
            values['name'] = defaults.get('name')
        return values
