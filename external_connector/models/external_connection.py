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


class ExternalConnection(models.Model):
    _name = "external.connection"
    _description = "External Connection"

    def _select_type(self):
        return [('none', 'None')]

    name = fields.Char(
        size=64,
        string="Connection",
        required=True
    )
    type = fields.Selection(
        selection=_select_type,
        string="Type",
        required=True
    )
    features = fields.One2many(
        comodel_name="external.connection.feature",
        inverse_name="connection",
        string="Features",
        help="Select Available Features of Connection"
    )
    active = fields.Boolean(
        string="Active"
    )
    description = fields.Text(
        string="Description"
    )

    @api.model
    def connect(self):
        self.ensure_one()
        conn = False
        return conn


    def external_create(self):

        return True

    def external_write(self):

        return True

    def external_unlink(self):

        return True

    def external_search(self):

        return True

    def external_read(self):

        return True