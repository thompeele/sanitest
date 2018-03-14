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
###############################################################################

import xmlrpclib
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MagentoAttribute(models.Model):
    _name = "magento.attribute"
    _description = "Magento Attribute"

    name = fields.Char(string='Code')
    type = fields.Char(string='Type')
    scope = fields.Char(string='Scope')
    required = fields.Char(string='Required')
    attribute_id = fields.Char(string='AttributeID', required=True)
    attribute_set_id = fields.Many2one(
        comodel_name="magento.attribute.set",
        string="Magento Attribute Set"
    )
    connection_id = fields.Many2one(
        comodel_name="magento.configure",
        string="Magento Connection"
    )

    @api.multi
    def get_attributes(self, attr_set, connection_id):
        """ Get Magento Attribute Sets
        :return: List of Attribute Sets
        """
        store_list = []
        values = {}
        config = self.env['magento.configure'].browse(connection_id)
        connection = config._create_connection()
        if connection:
            url = connection[0]
            session = connection[1]
            server = xmlrpclib.Server(url)

            try:
                attr_list = server.call(
                    session,
                    'catalog_product_attribute.list',
                    [attr_set.set_id]
                )
                values = {
                    'connection_id': connection[2].id,
                    'attr_list': attr_list
                }
            except xmlrpclib.Fault, e:
                return []
        _logger.debug("Attributes: %s", values)
        return values

    @api.multi
    def update_attributes(self, attr_set, connection_id):

        values = self.get_attributes(attr_set, connection_id)
        if values:
            attr_list = values['attr_list']

            for attr in attr_list:
                attribute = self.search([('attribute_id', '=', attr['attribute_id'])], limit=1)
                _logger.debug('Attribute Values: %s', attr)

                if attribute:
                    attribute.write(
                        {
                            'name': attr['code'],
                            'type': attr['type'],
                            'scope': attr['scope'],
                            'required': attr['required'],
                            'attribute_id': attr['attribute_id'],
                            'attribute_set_id': attr_set.id,
                            'connection_id': connection_id
                        }
                    )
                if not attribute:
                    attribute = self.create(
                        {
                            'name': attr['code'],
                            'type': attr['type'],
                            'scope': attr['scope'],
                            'required': attr['required'],
                            'attribute_id': attr['attribute_id'],
                            'attribute_set_id': attr_set.id,
                            'connection_id': connection_id
                        }
                    )

                self.env['magento.attribute.option'].update_attribute_options(attribute, connection_id)
