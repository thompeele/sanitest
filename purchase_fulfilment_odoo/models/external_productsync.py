# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2016 More2Make (www.more2make.nl).
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

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ExternalProductsync(models.Model):
    _inherit = 'external.productsync'

    @api.model
    def _get_external_product_code(self, product, partner):
        supinfo = self.env['product.supplierinfo'].search(
            [
                ('name', '=', partner.id),
                ('product_tmpl_id', '=', product.product_tmpl_id.id)
            ]
        )
        product_code = False
        if supinfo and supinfo[0]:
            product_code = supinfo[0].product_code

        return product_code or product.default_code

    @api.model
    def _get_product_by_suppliersku(self, supplier_sku, partner):
        _logger.debug("Parsing SKU %s", supplier_sku)
        supplier_product = self.env['product.supplierinfo'].search(
            [
                ('name', '=', partner.id),
                ('product_code', '=', supplier_sku)
            ]
        )
        if supplier_product and supplier_product[0]:
            return supplier_product[0].product_tmpl_id.product_variant_ids[0]

        #search by default_code
        product_product = self.env['product.product'].search(
            [
                ('seller_id', '=', partner.id),
                ('default_code', '=', supplier_sku)
            ]
        )
        if product_product and product_product[0]:
            return product_product[0]
        else:
            return False
