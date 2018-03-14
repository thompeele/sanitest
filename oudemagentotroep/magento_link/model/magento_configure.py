# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2015 ERP|OPEN (www.erpopen.nl).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import datetime
import xmlrpclib
import logging
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import Warning
import time

_logger = logging.getLogger(__name__)


class MagentoConfigure(models.Model):
    _name = "magento.configure"
    _inherit = ['mail.thread']
    _description = "Magento Configuration"

    @api.model
    def _lang_get(self):
        languages = self.env['res.lang'].search([])
        return [(language.code, language.name) for language in languages]

    name = fields.Char(string='Connection', required=True,
                       size=255)
    url = fields.Char(string='Base URL', required=True, size=255)
    user = fields.Char(string='API User Name', required=True, size=100)
    pwd = fields.Char(
        string='API Password',
        required=True,
        size=100,
        password=True
    )
    status = fields.Char(string='Connection Status', readonly=True, size=255)
    active = fields.Boolean(string='Active', default=lambda *a: 1)
    store_ids = fields.One2many(
        comodel_name='magento.store',
        inverse_name='connection_id',
        string='Magento Stores'
    )
    credential = fields.Boolean(
        string='Show/Hide Credentials Tab',
        help="If Enable, Credentials tab will be displayed, And after "
             "filling the details you can hide the Tab."
    )
    auto_invoice = fields.Boolean(
        string='Auto Invoice',
        default=lambda *a: 1,
        help='If Enabled, Order will automatically be Invoiced on Magento when'
             'ODOO order gets invoiced.'
    )
    auto_ship = fields.Boolean(
        string='Auto Shipment',
        default=lambda *a: 1,
        help='If Enabled, Order will automatically be shipped on Magento when '
             'ODOO order Get Delivered.'
    )
    create_date = fields.Datetime(string='Created Date')
    sync_min_date = fields.Datetime(string='Minimal Sync Date')
    lang = fields.Selection(
        selection='_lang_get',
        string='Language',
        help="Default Language for Connection",
        required=True)

    product_update_image = fields.Boolean(
        string='Update Image',
        default=lambda *a: 1,
        help="Update the image on Magento after product changes."
    )
    product_create_image = fields.Boolean(
        string='Upload Image',
        default=lambda *a: 1,
        help="Upload the image to Magento after product creation."
    )
    product_sync_delay = fields.Integer(
        string='Product Sync Delay',
        default=lambda *a: 5,
        help="Product Sync Delay in seconds."
    )

    @api.model
    def create(self, vals):
        active_ids = self.search([('active', '=', True)])
        if vals['active'] and active_ids:
            raise Warning(_("Sorry, Only one active connection is allowed."))
        return super(MagentoConfigure, self).create(vals)

    @api.multi
    def write(self, vals):
        active_ids = self.search([('active', '=', True)])
        if vals and len(active_ids) > 0 and vals.get('active'):
                raise Warning(_("Sorry, Only one active connection is allowed."))
        return super(MagentoConfigure, self).write(vals)

    @api.multi
    def test_connection(self):
        text = 'test connection Un-successful please check the magento api credentials!!!'
        status = 'Magento Connection Un-successful'
        url = self.url + '/index.php/api/xmlrpc'
        user = self.user
        pwd = self.pwd
        session = 0
        try:
            server = xmlrpclib.Server(url)
            session = server.login(user, pwd)
        except xmlrpclib.Fault, e:
            text = "Error, %s Invalid Login Credentials!!!" % (e.faultString)
        except IOError, e:
            text = str(e)
        except Exception, e:
            text = "Magento Connection in connecting: %s" % (e)
        if session:
            text = 'Test Connection with magento is successful, now you can proceed with synchronization.'
            status = "Congratulation, It's Successfully Connected with Magento Api."
        self.write({'status': status})
        partial = self.env['message.wizard'].create({'text': text})
        return {'name': _("Information"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'message.wizard',
                'res_id': partial.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                }

    @api.multi
    def _create_connection(self):
        """ create a connection between openerp and magento
            returns: False or list"""
        session = 0
        configs = self.search([('active', '=', True)])
        if not configs:
            raise Warning(_("Please create the configuration part for Magento connection!!!"))
        elif configs and len(configs) > 1:
            raise Warning(_("Sorry, only one Active Configuration setting is allowed."))
        else:
            obj = configs[0]
            url = obj[0].url + '/index.php/api/xmlrpc'
            user = obj[0].user
            pwd = obj[0].pwd
            try:
                server = xmlrpclib.Server(url)
                session = server.login(user, pwd)
            except xmlrpclib.Fault, e:
                raise Warning(_("Invalid Login Credentials!!! %s") % e.faultString)
            except IOError, e:
                raise Warning(_(" %s") % e)
            except Exception, e:
                raise Warning(_("Magento Connection Error in connecting: %s") % e)
            if session:
                return [url, session, obj]
            else:
                return False

    @api.multi
    def button_sync_order(self):
        """
        Method for syncing orders from a certain date or id from Magento to ODOO
        :return:
        """
        _logger.debug("Button Sync Order")
        for rec in self:
            rec.sync_order()

    @api.model
    def sync_order(self):
        """
        Method for syncing orders from a certain date or id from Magento to ODOO
        :return:
        """
        _logger.debug("Sync Order")

        connection = self._create_connection()
        url = connection[0]
        session = connection[1]
        server = xmlrpclib.Server(url)

        orders = self.env['sale.order'].search(
            [
                ('magento_order', '!=', False)
            ],
            order="date_order"
        )

        if not orders:
            min_date = '2017-01-01 00:00:00'

        # Determine the minimal date
        if self.sync_min_date:
            min_date = self.sync_min_date
        elif orders:
            min_date = orders[0].date_order

        max_date = (datetime.datetime.now() - datetime.timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')

        if not min_date:
            raise Exception('No magento order found to determine min date for cron magento order sync')
        _logger.debug('CRON: syncing orders between %s and %s' % (min_date, max_date))
        server.call(session, 'odoolink.syncByDate', [min_date, max_date])

        return True
