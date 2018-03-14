from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    magento_code = fields.Char(string='Magento code')
    additional_costs = fields.Many2one('product.product', string='Additional Costs')
    can_pay_in_advance = fields.Boolean(string='Allowed to pay in after shipment', help="example: pay at delivery")
