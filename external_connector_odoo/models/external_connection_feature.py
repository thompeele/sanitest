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
    _inherit = "external.connection.feature"

    def _connection_feature(self):
        return_list = super(ExternalConnectionFeature, self)._connection_feature()

        available_types = [
            ('create', 'Create'),
            ('write', 'Write'),
            ('search', 'Search'),
            ('read', 'Read'),
            ('unlink', 'Unlink')
        ]
        for available_type in available_types:
            if not available_type in return_list:
                return_list.append(available_type)
        return return_list

    name = fields.Selection(
            selection=_connection_feature,
    )