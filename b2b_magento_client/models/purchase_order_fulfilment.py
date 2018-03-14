# -*- coding: utf-8 -*-
# Copyright© 2015 ERPOpen <http://www.erpopen.nl>
# License: AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
from odoo import models, fields, api, _
from odoo.exceptions import Warning as UserError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def prepare_external_values(self):
        self.ensure_one()
        values = {}
        values['OrderRef'] = self.sale_order_ids and self.sale_order_ids[0].name or self.name
        if self.sale_order_ids and self.sale_order_ids[0].magento_id:
            values['MagOrderRef'] =  self.sale_order_ids[0].magento_id
        values['CustomerRef'] = self.external_fulfilment_partner.external_id
        return values
