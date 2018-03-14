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
from odoo.tools.translate import _
import odoo.netsvc


######################## Mapping update Model(Used from server action) #########################

class mapping_update(models.TransientModel):
    _name = "mapping.update"

    need_sync = fields.Selection([('Yes', 'Yes'), ('No', 'No')],
                                 'Update Required')

    @api.model
    def open_update_wizard(self):
        vals = {}
        partial = self.create(vals)
        return {'name': _("Bulk Action"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'mapping.update',
                'res_id': partial.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'context': self._context,
                'domain': '[]'}

    @api.multi
    def update_mapping_status(self):
        count = 0
        model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        status = self.browse(self._ids[0]).need_sync
        for i in active_ids:
            rec = self.env[model].search([('id', '=', i)])
            rec.write({'need_sync': status})
            count = count + 1
        text = 'Status of %s record has been successfully updated to %s.' % (count, status)
        partial = self.env['message.wizard'].create({'text': text})
        return {'name': _("Information"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'message.wizard',
                'res_id': partial.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new'}

mapping_update()
