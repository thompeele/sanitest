from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def prepare_external_values(self):
        values = super(PurchaseOrder, self).prepare_external_values()
        values['shipping_method'] = self.sale_order_ids and self.sale_order_ids[0].shipping_method or False
        values['shipping_method_data'] = self.sale_order_ids and self.sale_order_ids[0].shipping_method_data or False
        return values