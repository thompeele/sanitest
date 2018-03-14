from odoo import api, fields, models, _


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"
    _order = 'sequence, id'

    magento_code = fields.Char(string='Magento code')