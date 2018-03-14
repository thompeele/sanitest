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


class ExternalMapping(models.Model):
    _name = "external.mapping"
    _description = "External Mapping"


    external_id = fields.Char(
        size=64,
        string="Unique External ID",
        required=True,
        index=True
    )
    model = fields.Char(
        string="Model",
        required=True,
        index=True
    )
    res_id = fields.Integer(
        string="Resource ID",
        index=True
    )
    connection = fields.Many2one(
        comodel_name='external.connection',
        string="Connection",
        index=True
    )

