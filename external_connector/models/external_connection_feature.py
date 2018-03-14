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


class ExternalConnectionFeature(models.Model):
    _name = "external.connection.feature"
    _description = "External Connection Features"

    def _connection_feature(self):
        return [('none', 'None')]

    name = fields.Selection(
        selection=_connection_feature,
        string="Type",
        required=True
    )

    connection = fields.Many2one(
        comodel_name="external.connection",
        required=True
    )