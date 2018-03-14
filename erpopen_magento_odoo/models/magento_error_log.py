import datetime
from odoo import fields, models, api


class magento_error_log(models.Model):
    _name = 'magento.error.log'
    _order = 'date desc'

    # id = fields.Integer()
    name = fields.Char('name', store=True)
    message = fields.Char('message', store=True)
    date = fields.Datetime(default=lambda self: fields.datetime.now())
    level = fields.Selection([('Info', 'Info'),  ('Warning', 'Warning'), ('Error', 'Error')], string='Log Level', required=True, default='Error')
    company_id = fields.Many2one('res.company', string='Company')

    def action_clear_all(self):
        self.search([('id', '!=', -1)]).unlink()

    def cleanup(self):
        logs_to_delete = self.search([('level', 'in', ['Info', 'Warning'])])
        last_id = logs_to_delete and max(logs_to_delete)
        self.search(['&', ('level', '=', ['Info', 'Warning']), ('id', '<', last_id.id - 250)]).unlink()
