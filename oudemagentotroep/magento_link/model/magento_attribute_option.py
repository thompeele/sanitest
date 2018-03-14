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
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class MagentoAttributeOption(models.Model):
    _name = "magento.attribute.option"
    _description = "Magento Attribute Option"

    name = fields.Char(string='Label')
    value = fields.Char(string='Value')
    active = fields.Boolean(default=True)
    attribute_id = fields.Many2one(
        comodel_name='magento.attribute',
        string='Attribute',
        required=True
    )

    @api.multi
    def get_attribute_options(self, attribute, connection_id):
        """ Get Magento Attribute Option for Attribute
        :return: List of Attribute Options
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
                attr_option_list = server.call(
                    session,
                    'catalog_product_attribute.options',
                    [attribute.attribute_id]
                )
                values = {
                    'connection_id': connection[2].id,
                    'list': attr_option_list
                }
            except xmlrpclib.Fault, e:
                return []
        _logger.debug("Attribute Options: %s", values)
        return values

    @api.multi
    def update_attribute_options(self, attribute, connection_id):

        values = self.get_attribute_options(attribute, connection_id)
        if values:
            attr_option_list = values['list']
            update_option_ids = []
            for option in attr_option_list:
                if option.get('label') and option.get('value'):
                    searchrecord = self.with_context(active_test=False).search(
                            [
                                ('name', '=', option.get('label')),
                                ('value', '=', option.get('value')),
                                ('attribute_id', '=', attribute.id),
                            ],
                            limit=1
                    )

                    if searchrecord:
                        searchrecord.active = True
                        update_option_ids.append(searchrecord.id)
                    if not searchrecord:
                        createrecord = self.create(
                                {
                                    'name': option.get('label'),
                                    'value': option.get('value'),
                                    'attribute_id': attribute.id,
                                    'active': True
                                }
                        )
                        update_option_ids.append(createrecord.id)

            options = self.search([('attribute_id', '=', attribute.id)])
            if options:
                for option in options:
                    if option.id not in update_option_ids:
                        option.active = False
