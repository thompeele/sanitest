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


class MagentoStore(models.Model):
    _name = "magento.store"
    _description = "Magento Stores"

    @api.model
    def _lang_get(self):
        languages = self.env['res.lang'].search([])
        return [(language.code, language.name) for language in languages]

    name = fields.Char(string='Name', required=True,
                       size=64)
    code = fields.Char(string='Code', required=True,
                       size=64)
    store_id = fields.Integer(string='StoreId')
    website_id = fields.Integer(string='WebsiteId')
    group_id = fields.Integer(string='GroupId')
    active = fields.Boolean(string='Active')
    connection_id = fields.Many2one(
        comodel_name='magento.configure', string='Magento Connection'
    )
    sales_team_id = fields.Many2one(
        comodel_name='crm.team', string='Sales Team'
    )
    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist', string='Used Pricelist'
    )
    lang = fields.Selection(selection='_lang_get',
                            string='Language',
                            help="Default Language for Store")

    @api.multi
    def get_stores(self):
        """ Get Magento Stores
        :return: List of Magento Stores
        """
        store_list = []
        values = {}
        configs = self.env['magento.configure'].search([('active', '=', True)])
        for config in configs:
            connection = config._create_connection()
            if connection:
                url = connection[0]
                session = connection[1]
                server = xmlrpclib.Server(url)

                try:
                    store_list = server.call(session, 'store.list')
                    values = {'connection_id': connection[2].id,
                              'store_list': store_list}
                except xmlrpclib.Fault, e:
                    return []
        return values

    @api.multi
    def update_stores(self, store=False):

        ctx = self.env.context.copy()
        ctx.update({'activetest': False})

        link_store_list = []
        values = self.get_stores()
        if values:
            store_list = values['store_list']
            connection_id = values['connection_id']
            for store in store_list:
                searchrecords = self.with_context(ctx).search([('store_id', '=', store['store_id'])])
                for record in searchrecords:
                    record.write(
                        {
                            'name': store['name'],
                            'store_id': store['store_id'],
                            'website_id': store['website_id'],
                            'group_id': store['group_id'],
                            'active': True,
                            'code': store['code'],
                            'connection_id': connection_id
                        }
                    )
                if not searchrecords:
                    self.create(
                        {
                            'name': store['name'],
                            'store_id': store['store_id'],
                            'website_id': store['website_id'],
                            'group_id': store['group_id'],
                            'active': True,
                            'code': store['code'],
                            'connection_id': connection_id
                        }
                    )

                try:
                    link_store_list.append(int(store['store_id']))
                except:
                    link_store_list.append(store['store_id'])

            # Deactivate Inactive or non existing stores
            for link_store in self.with_context(ctx).search([]):

                if link_store.store_id in link_store_list:
                    link_store.active = True
                else:
                    link_store.active = False
