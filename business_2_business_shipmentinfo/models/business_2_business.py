from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class Business2Business(models.Model):
    _inherit = 'business.2.business'

    @api.model
    def _process_order_values(self, values, partner):
        order_values = super(Business2Business,self)._process_order_values(values, partner)
        if values.get('shipping_method'):
            order_values['shipping_method'] = values.get('shipping_method')
        if values.get('shipping_method_data'):
            order_values['shipping_method_data'] = values.get('shipping_method_data')
        return order_values