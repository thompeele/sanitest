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

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    external_fulfilment_partners = fields.One2many(
            comodel_name="external.fulfilment.partner",
            inverse_name='partner',
            string="External FulFilments"
    )

    @api.model
    def get_external_values(self):
        self.ensure_one()
        values = {
            'name': self.name,
            'street': self.street,
            'zipcode': self.zip,
            'city': self.city,
            'countrycode': self.country_id and self.country_id.code,
            'email': self.email,
            'telephone': self.phone
        }
        if self.parent_id:
            values.update({
                'company': self.parent_id.name,
                'name': self.name
            })
        if 'street_number_ext' in self._fields:
            values.update({
                'street': self.street_name,
                'housenumber': self.street_number,
                'housenumberaddition': self.street_number_ext
            })
        return values