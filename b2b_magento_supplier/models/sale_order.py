# -*- encoding: utf-8 -*-

import xmlrpclib
import logging
import urllib
from odoo import fields, models

_logger = logging.getLogger(__name__)


class sale_order(models.Model):
    _inherit = "sale.order"

    magento_order_ext = fields.Char(string='External Magento Order', size=128)