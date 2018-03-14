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
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_available = fields.Float(
            compute="_new_product_available",
            search="_search_product_qty_available"
    )
    virtual_available = fields.Float(
            compute="_new_product_available",
            search="_search_product_qty_available"
    )
    incoming_qty = fields.Float(
            compute="_new_product_available",
            search="_search_product_qty_available"
    )
    outgoing_qty = fields.Float(
            compute="_new_product_available",
            search="_search_product_qty_available"
    )
    external_fulfilment_qty = fields.Float(
        string="External available QTY"
    )

    external_fulfilment_eol = fields.Boolean(
            string="External End of Life",
            default=False
    )


    def _search_product_qty_available(self, operator, value):
        res = self._search_product_filter_quantity(operator, value, 'qty_available')
        return res

    def _search_product_virtual_available(self, operator, value):
        res = self._search_product_filter_quantity(operator, value, 'virtual_available')
        return res

    def _search_product_incoming_qty(self, operator, value):
        res = self._search_product_filter_quantity(operator, value, 'incoming_qty')
        return res


    def _search_product_outgoing_qty(self, operator, value):
        res = self._search_product_filter_quantity(operator, value, 'outgoing_qty')
        return res

    def _get_qty_filter_fields(self):
        return  ['qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty']

    def _search_product_filter_quantity(self, operator, value, filter_field):
        res = []
        ids = []
        assert filter_field in self._get_qty_filter_fields(), 'Invalid domain left operand'
        assert operator in ('<', '>', '=', '!=', '<=', '>='), 'Invalid domain operator'
        assert isinstance(value, (float, int)), 'Invalid domain right operand'
        if operator == '=':
            operator = '=='

        if filter_field == 'qty_available' and (value != 0.0 or operator not in  ('==', '>=', '<=')):
            qty_available_ids = self._search_product_filter_qty_available(operator, value)
            external_prod_ids = self._search_all_product_ids_external()
            external_qty_ids = self._search_product_filter_external_qty(operator, value, external_prod_ids)
            qty_available_ids = [x for x in qty_available_ids if x not in external_prod_ids]
            qty_available_ids.extend(external_qty_ids)
            res.append(('id', 'in', qty_available_ids))
        else:
            products = self.search([])

            if products:
                #TODO: Still optimization possible when searching virtual quantities
                for element in products:
                    if eval(str(element[filter_field]) + operator + str(value)):
                        ids.append(element.id)
            res.append(('id', 'in', ids))
        return res

    def _search_product_filter_qty_available(self, operator, value):
        domain_quant = []
        if self._context.get('lot_id'):
            domain_quant.append(('lot_id', '=', self._context['lot_id']))
        if self._context.get('owner_id'):
            domain_quant.append(('owner_id', '=', self._context['owner_id']))
        if self._context.get('package_id'):
            domain_quant.append(('package_id', '=', self._context['package_id']))
        domain_quant += self._get_domain_locations()[0]
        quants = self.pool.get('stock.quant').read_group(self._cr, self._uid, domain_quant, ['product_id', 'qty'], ['product_id'], context=self._context)
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))
        quants = dict((k, v) for k, v in quants.iteritems() if eval(str(v) + operator + str(value)))
        return list(quants)

    def _search_product_filter_external_qty(self, operator, value, external_ids):
        external_prods = self.search([('id', 'in', external_ids)])
        external_prods = external_prods.filtered(lambda p: eval(str(p.external_fulfilment_qty) + operator + str(value)))
        return external_prods.ids

    def _search_all_product_ids_external(self):
        ff_partners = self.env['external.fulfilment.partner'].search([])
        partners = ff_partners.mapped('partner')
        products = self.search([('seller_id', 'in', partners.ids)])
        return products.ids

    @api.multi
    def check_fulfil_product(self):
        self.ensure_one()
        if self.seller_ids:
            fulfil_partners = self.env['external.fulfilment.partner'].search(
                    [
                        ('partner', 'in', self.seller_ids.ids)
                    ]
            )
            if len(fulfil_partners) >= 1:
                return True
        return False

    @api.multi
    def _new_product_available(self):
        domain_products = [('product_id', 'in', self.ids)]
        domain_quant, domain_move_in, domain_move_out = [], [], []
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_move_in += [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_move_out += [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
        domain_quant += domain_products

        if self._context.get('lot_id'):
            domain_quant.append(('lot_id', '=', self._context['lot_id']))
        if self._context.get('owner_id'):
            domain_quant.append(('owner_id', '=', self._context['owner_id']))
            owner_domain = ('restrict_partner_id', '=', self._context['owner_id'])
            domain_move_in.append(owner_domain)
            domain_move_out.append(owner_domain)
        if self._context.get('package_id'):
            domain_quant.append(('package_id', '=', self._context['package_id']))

        domain_move_in += domain_move_in_loc
        domain_move_out += domain_move_out_loc
        moves_in = self.env['stock.move'].read_group(domain_move_in, ['product_id', 'product_qty'], ['product_id'])
        moves_out = self.env['stock.move'].read_group(domain_move_out, ['product_id', 'product_qty'], ['product_id'])

        domain_quant += domain_quant_loc
        quants = self.env['stock.quant'].read_group(domain_quant, ['product_id', 'qty'], ['product_id'])
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))

        moves_in = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_in))
        moves_out = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_out))

        for product in self:
            id = product.id
            qty_available = float_round(quants.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            incoming_qty = float_round(moves_in.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            outgoing_qty = float_round(moves_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            virtual_available = float_round(quants.get(id, 0.0) + moves_in.get(id, 0.0) - moves_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)

            if product.check_fulfil_product():
                product.qty_available = product.external_fulfilment_qty or 0.0
                product.incoming_qty = incoming_qty or 0.0
                product.outgoing_qty = outgoing_qty or 0.0
                product.virtual_available = product.external_fulfilment_qty or 0.0
            else:
                product.qty_available = qty_available or 0.0
                product.incoming_qty = incoming_qty or 0.0
                product.outgoing_qty = outgoing_qty or 0.0
                product.virtual_available = virtual_available or 0.0