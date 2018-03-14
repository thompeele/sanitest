from odoo import api, fields, models, _

class SK_Invoice(models.Model):
    _inherit = "account.invoice"

    magento_order_ext = fields.Char ('Magento Order Ext')