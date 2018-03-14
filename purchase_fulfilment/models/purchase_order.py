# -*- coding: utf-8 -*-
# Copyright© 2015 ICTSTUDIO <http://www.ictstudio.eu>
# License: AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
from odoo import models, fields, api, _
from odoo.exceptions import Warning as UserError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    external_fulfilment_partner = fields.Many2one(
        comodel_name="external.fulfilment.partner",
        string="External FulFilment",
        compute="_compute_external_fulfilment_partner",
        store=True
    )
    external_id = fields.Char(
        string='External Identifier'
    )
    external_state = fields.Char(
        string='External State',
        track_visibility='always'
    )

    @api.model
    def get_external_fulfilment_partner(self):

        section_id = self.sale_order_ids and self.sale_order_ids[0].team_id or False

        efps = self.env['external.fulfilment.partner'].search(
                [
                    ('partner', '=', self.partner_id.id),
                ]
        )

        if efps and len(efps) == 1:
            return efps[0]
        elif efps:
            efp_defaults = efps.filtered(lambda e: not e.sales_team_id)
            if efp_defaults:
                efp_default = efp_defaults[0]
                _logger.debug("EFP Default: %s", efp_default)
                if section_id:
                    efp_sections = efps.filtered(lambda e: e.sales_team_id == section_id)
                    if efp_sections:
                        _logger.debug("EFP Sections: %s", efp_sections[0])
                        return efp_sections[0]
                return efp_default
        else:
            return False


    @api.one
    @api.depends('partner_id', 'state')
    def _compute_external_fulfilment_partner(self):
        self.external_fulfilment_partner = self.get_external_fulfilment_partner()

    @api.multi
    def button_confirm(self):
        _logger.debug('Button Confirm')
        res = super(PurchaseOrder, self).button_confirm()
        for rec in self:
            if rec.external_fulfilment_partner and not rec.external_id:
                _logger.debug('Fulfil Send Order')
                rec.external_id, rec.external_state = rec.fulfil_send_order()
        return res
		
    @api.model
    def _get_product_code(self, line):
        supinfo = self.env['product.supplierinfo'].search(
                [
                    ('name', '=', line.partner_id.id),
                    ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)
                ]
        )
        return supinfo and supinfo.product_code or line.product_id.default_code

    @api.model
    def prepare_external_send_order_values(self):
        self.ensure_one()
        values = self.prepare_external_values()
        values['Address'] = self.get_shipping_address()
        values['Lines'] = []
        for line in self.order_line:
            line_vals={}
            line_vals['Quantity'] = line.product_qty
            line_vals['ProductCode'] = self._get_product_code(line)
            values['Lines'].append(line_vals)
        return values

    @api.model
    def prepare_external_cancel_order_values(self):
        self.ensure_one()
        values = self.prepare_external_values()
        return values

    @api.model
    def prepare_external_values(self):
        self.ensure_one()
        values = {}
        values['OrderRef'] = self.sale_order_ids and self.sale_order_ids[0].name or self.name
        values['CustomerRef'] = self.external_fulfilment_partner.external_id
        return values

    @api.model
    def get_shipping_address(self):
        self.ensure_one()
        sale_order = self.sale_order_ids and self.sale_order_ids[0]
        partner = sale_order.partner_shipping_id or sale_order.partner_id
        return partner.get_external_values()


    @api.multi
    def fulfil_send_order(self):
        """
        Hook to provide fulfil send order functionality
        :return:
        """
        self.ensure_one()
        return False, False

    @api.multi
    def button_cancel(self):

        for rec in self:
            _logger.debug('Order canceled')
            rec.external_state, cancel_succesfull = rec.fulfil_cancel_order()
            if cancel_succesfull:
                super(PurchaseOrder, rec).button_cancel()
            else:
                raise UserError (
                        _("Unable to Cancel Order Remote") + '. ' + _("Order is being processed in Supplier Warehouse. You need to Call!")
                )
        return False

    @api.multi
    def fulfil_cancel_order(self):
        """
        Hook to provide fulfil send order functionality
        :return:
        """
        self.ensure_one()
        return False, False