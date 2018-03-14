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

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
import odoo.netsvc
import logging
import xmlrpclib


class message_wizard(models.TransientModel):
    _name = "message.wizard"

    text = fields.Text('Message', readonly=True, translate=True)

message_wizard()


class region_wizard(models.TransientModel):
    _name = "region.wizard"

    country_ids = fields.Many2one('res.country', 'Country')

    @api.model
    def _sync_mage_region(self, url, session, country_code):
        dlist = {}
        ddict = {}
        server = xmlrpclib.Server(url)
        try:
            regions = server.call(session, 'region.list', [country_code])
        except xmlrpclib.Fault, e:
            raise UserError(_(' %s') % e)
        if regions:
            for i in regions:
                dlist['name'] = i['name']
                dlist['region_code'] = i['code']
                dlist['country_code'] = country_code
                dlist['mag_region_id'] = i['region_id']
                self.env['magento.region'].create(dlist)
                if country_code != 'US':
                    country_ids = self.env['res.country'].search([(
                        'code', '=', country_code)])
                    ddict['name'] = i['name']
                    ddict['country_id'] = country_ids[0].id
                    ddict['code'] = i['name'][:2].upper()
                    self.env['res.country.state'].create(ddict)
            return len(regions)
        else:
            return 0

    @api.multi
    def sync_state(self):
        self.ensure_one()
        config_id = self.env['magento.configure'].search([('active', '=', True)])
        if len(config_id) > 1:
            raise UserError(_('Sorry, only one Active Configuration setting is allowed.'))
        if not config_id:
            raise UserError(_('Please create the configuration part for connection!!!'))
        else:
            obj = self.env['magento.configure'].browse(config_id[0].id)
            url = obj.url + '/index.php/api/xmlrpc'
            user = obj.user
            pwd = obj.pwd
            try:
                logging.info("2222 %s"%url)
                server = xmlrpclib.Server(url)
                logging.info("2222 %s"%server)
                session = server.login(user, pwd)
                logging.info("2222 %s"%session)
            except xmlrpclib.Fault, e:
                raise UserError(_('Invalid Information'))
            except IOError, e:
                raise UserError(_(' %s') % e)
            except Exception, e:
                raise UserError(_('Magento Connection " + netsvc.LOG_ERROR +  " in connecting: %s') % e)
            if session:
                country_id = self.browse(self._ids[0]).country_ids
                country_code = country_id.code
                map_id = self.env['magento.region'].search([('country_code', '=', country_code)])
                if not map_id:
                    total_regions = self._sync_mage_region(url, session, country_code)
                    if total_regions == 0:
                        raise UserError(_('There is no any region exist for country %s.') % (country_id.name))
                        return {
                            'type': 'ir.actions.act_window_close',
                        }
                    else:
                        text = "%s Region of %s are sucessfully Imported to OpenERP." % (total_regions, country_id.name)
                        partial = self.env['message.wizard'].create({'text': text})
                        return {'name': _("Message"),
                                'view_mode': 'form',
                                'view_id': False,
                                'view_type': 'form',
                                'res_model': 'message.wizard',
                                'res_id': partial.id,
                                'type': 'ir.actions.act_window',
                                'nodestroy': True,
                                'target': 'new',
                                'domain': '[]'}
                else:
                    raise UserError(_('All regions of %s are already imported to OpenERP.') % (country_id.name))
region_wizard()
