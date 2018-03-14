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

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

try:
    import erppeek
except ImportError:
    _logger.debug('Cannot `import erppeek`.')


class ExternalConnection(models.Model):
    _inherit = "external.connection"

    def _select_type(self):
        return_list = super(ExternalConnection, self)._select_type()
        return_list.append(('odoo_xmlrpc','ODOO XMLRPC'))
        return return_list

    type = fields.Selection(
            selection=_select_type,
            string="Type",
            required=True
    )
    odoo_xmlrpc_server = fields.Char(
        size=128,
        string="Server"
    )
    odoo_xmlrpc_user = fields.Char(
        size=128,
        string="User"
    )
    odoo_xmlrpc_password = fields.Char(
        size=128,
        string="Password"
    )
    odoo_xmlrpc_database = fields.Char(
            size=128,
            string="Database"
    )

    @api.model
    def connect(self):
        self.ensure_one()

        conn = super(ExternalConnection, self).connect()

        if self.type == 'odoo_xmlrpc':
            _logger.debug("ODOOXMLRPC-Connection")
            try:
                conn = erppeek.Client(self.odoo_xmlrpc_server,self.odoo_xmlrpc_database,self.odoo_xmlrpc_user,self.odoo_xmlrpc_password)
            except Exception as e:
                _logger.error("Error connecting to ODOO Server")
        return conn


    def external_create(self, values):
        return_val = super(ExternalConnection, self).external_create(values)

        if self.type == 'odoo_xmlrpc':
            # Create Code
            _logger.debug("ODOOXMLRPC-Create")
        return return_val

    def external_write(self, values):
        return_val = super(ExternalConnection, self).external_write(values)

        if self.type == 'odoo_xmlrpc':
            # Write Code
            _logger.debug("ODOOXMLRPC-Write")
        return return_val

    def external_unlink(self):
        return_val = super(ExternalConnection, self).external_unlink()

        if self.type == 'odoo_xmlrpc':
            # Unlink Code
            _logger.debug("ODOOXMLRPC-Unlink")
        return return_val

    def external_search(self):
        return_val = super(ExternalConnection, self).external_search()

        if self.type == 'odoo_xmlrpc':
            # Search Code
            _logger.debug("ODOOXMLRPC-Search")
        return return_val

    def external_read(self):
        return_val = super(ExternalConnection, self).external_read()

        if self.type == 'odoo_xmlrpc':
            # Read Code
            _logger.debug("ODOOXMLRPC-Read")
        return return_val
