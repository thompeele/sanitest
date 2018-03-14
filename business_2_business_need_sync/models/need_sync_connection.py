# -*- coding: utf-8 -*-
# Copyright© 2016 ICTSTUDIO <http://www.ictstudio.eu>
# License: AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class NeedSyncConnection(models.Model):
    _inherit = "need.sync.connection"

    def _select_models(self):
        list_models = super(NeedSyncConnection, self)._select_models()
        list_models.append(('business.2.business','Business2Business'))
        return list_models

    connection = fields.Reference(
            string="Connection",
            selection=_select_models,
            required=True,
            size=128
    )

    @api.one
    @api.depends('connection')
    def _get_name(self):
        if self.connection and self.connection._name=='business.2.business':
            self.name = 'Business2Business: %s' % (self.connection.partner_id.name)
        else:
            super(NeedSyncConnection, self)._get_name()


