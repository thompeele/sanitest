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


class MagentoAttributeSet(models.Model):
    _name = "magento.attribute.set"
    _description = "Magento Attribute Set"

    name = fields.Char(string='Name', required=True,
                       size=64)
    set_id = fields.Char(string='Code', required=True)
    connection_id = fields.Many2one(
        comodel_name='magento.configure',
        string='Magento Connection'
    )

    @api.multi
    def get_attribute_sets(self):
        """ Get Magento Attribute Sets
        :return: List of Attribute Sets
        """
        store_list = []
        values = {}
        configs = self.env['magento.configure'].search(
            [
                (
                    'active',
                    '=',
                    True
                )
            ]
        )
        for config in configs:
            connection = config._create_connection()
            if connection:
                url = connection[0]
                session = connection[1]
                server = xmlrpclib.Server(url)

                try:
                    store_list = server.call(
                        session,
                        'catalog_product_attribute_set.list'
                    )
                    values = {
                        'connection_id': connection[2].id,
                        'set_list': store_list
                    }
                except xmlrpclib.Fault, e:
                    return []
        return values

    @api.multi
    def update_attribute_sets(self):
        """ Update Attribute Sets"""
        values = self.get_attribute_sets()
        if values:
            set_list = values['set_list']
            connection_id = values['connection_id']
            for attr_set in set_list:
                searchrecords = self.search([
                    ('set_id', '=', attr_set['set_id'])])
                for record in searchrecords:
                    record.write(
                        {
                            'name': attr_set['name'],
                            'set_id': attr_set['set_id'],
                            'connection_id': connection_id
                        }
                    )
                    attr_set = record
                if not searchrecords:
                    attr_set = self.create(
                        {
                            'name': attr_set['name'],
                            'set_id': attr_set['set_id'],
                            'connection_id': connection_id
                        }
                    )

                self.env['magento.attribute'].update_attributes(attr_set, connection_id)
