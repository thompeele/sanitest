from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    shipping_method = fields.Char(
            size=64,
            string="Shipping Method"
    )
    shipping_method_data = fields.Text(
            string="Shipping Method Data"
    )
