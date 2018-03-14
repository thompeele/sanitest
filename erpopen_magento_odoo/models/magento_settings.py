from odoo import models,api,fields
from odoo.osv import osv


class magento_settings(models.Model):
    _name = 'magento.settings'

    name = fields.Char(String="Name")
    company = fields.Many2one("res.company", string="Company")
    url = fields.Char(String="Url Magento")
    username = fields.Char(String="Web Service Username")
    password = fields.Char(String="Web Service Password")
    incremental_imports = fields.Boolean(string="Incremental import", help="works only for customers, products and sales orders", store=True)
    manual_import_product_magento_id = fields.Char(String="Manual import product magento id")
    manual_import_sale_order_magento_id = fields.Char(String="Manual import sale order magento id")

    import_categories_interval_time = fields.Integer()
    import_categories_interval_units = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('work_days', 'Work Days'), ('days', 'Days'),
         ('weeks', 'Weeks'), ('months', 'Months')])
    import_attributes_interval_time = fields.Integer()
    import_attributes_interval_units = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('work_days', 'Work Days'), ('days', 'Days'),
         ('weeks', 'Weeks'), ('months', 'Months')])
    import_customers_interval_time = fields.Integer()
    import_customers_interval_units = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('work_days', 'Work Days'), ('days', 'Days'),
         ('weeks', 'Weeks'), ('months', 'Months')])
    import_products_interval_time = fields.Integer()
    import_products_interval_units = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('work_days', 'Work Days'), ('days', 'Days'),
         ('weeks', 'Weeks'), ('months', 'Months')])
    import_products_stock_interval_time = fields.Integer()
    import_products_stock_interval_units = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('work_days', 'Work Days'), ('days', 'Days'),
         ('weeks', 'Weeks'), ('months', 'Months')])
    import_sales_orders_interval_time = fields.Integer()
    import_sales_orders_interval_units = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('work_days', 'Work Days'), ('days', 'Days'),
         ('weeks', 'Weeks'), ('months', 'Months')])

    magento_sale_order_prefix = fields.Char()
    magento_invoice_prefix = fields.Char()
    magento_sale_order_status = fields.Selection(selection=[('canceled', 'Canceled'), ('pending', 'Pending'),('complete', 'Complete'),
                                                            ('processing', 'Processing'),('onhold', 'On Hold')])
    enable_syncing_to_magento = fields.Boolean(string="Warning, when enabled odoo will write to your shop.")
    magento_customer_email = fields.Char()
    magento_product_simple_product = fields.Boolean()
    magento_sale_order_from = fields.Datetime()
    magento_sale_order_to = fields.Datetime()
    magento_sale_order_auto_invoice = fields.Boolean()

    magento_account_id = fields.Many2one('account.account')
    magento_company_id = fields.Many2one('res.company')
    magento_currency_id = fields.Many2one('res.currency')
    magento_journal_id = fields.Many2one('account.journal')
    magento_sale_journal_id = fields.Many2one('account.journal')

    magento_sale_order_from_ecommerce = fields.Boolean(default=False)
    magento_time_zone_adjustment = fields.Integer(default=0)


    def create_cron_categories(self):
        if self.import_categories_interval_time and self.import_categories_interval_units:
            cron_name = 'magento_categories' + str(self.id)
            exist = self.env['ir.cron'].search([('name', '=', cron_name)])
            function_name = 'cron_category_magento'
            if self.incremental_imports:
                function_name += '_incremental'
            vals = {
                'name': 'magento_categories',
                'interval_number': int(self.import_categories_interval_time),
                'interval_type': self.import_categories_interval_units,
                'model': 'magento.sync',
                'numbercall': -1,
                'function': function_name
            }
            if not exist:
                self.env['ir.cron'].create(vals)
            else:
                exist.write(vals)
        else:
            raise osv.except_osv(('Error'), ('Insert interval number and unit'))

    def create_cron_customers(self):
        if self.import_categories_interval_time and self.import_categories_interval_units:
            cron_name = 'magento_customers' + str(self.id)
            exist = self.env['ir.cron'].search([('name', '=', cron_name)])
            function_name = 'cron_customer_magento'
            if self.incremental_imports:
                function_name += '_incremental'
            vals = {
                'name': 'magento_customers',
                'interval_number': int(self.import_customers_interval_time),
                'interval_type': self.import_customers_interval_units,
                'model': 'magento.sync',
                'numbercall': -1,
                'function': function_name
            }
            if not exist:
                self.env['ir.cron'].create(vals)
            else:
                exist.write(vals)
        else:
            raise osv.except_osv(('Error'), ('Insert interval number and unit'))

    def create_cron_attribute(self):
        if self.import_categories_interval_time and self.import_categories_interval_units:
            cron_name = 'magento_attribute' + str(self.id)
            exist = self.env['ir.cron'].search([('name', '=', cron_name)])
            function_name = 'cron_attribute_magento'
            if self.incremental_imports:
                function_name += '_incremental'
            vals = {
                'name': 'magento_attribute',
                'interval_number': int(self.import_attributes_interval_time),
                'interval_type': self.import_attributes_interval_units,
                'model': 'magento.sync',
                'numbercall': -1,
                'function': function_name
            }
            if not exist:
                self.env['ir.cron'].create(vals)
            else:
                exist.write(vals)
        else:
            raise osv.except_osv(('Error'), ('Insert interval number and unit'))

    def create_cron_products(self):
        if self.import_categories_interval_time and self.import_categories_interval_units:
            cron_name = 'magento_product' + str(self.id)
            exist = self.env['ir.cron'].search([('name', '=', cron_name)])
            function_name = 'cron_product_magento'
            if self.incremental_imports:
                function_name += '_incremental'
            vals = {
                'name': 'magento_product',
                'interval_number': int(self.import_products_interval_time),
                'interval_type': self.import_products_interval_units,
                'model': 'magento.sync',
                'numbercall': -1,
                'function': function_name
            }
            if not exist:
                self.env['ir.cron'].create(vals)
            else:
                exist.write(vals)
        else:
            raise osv.except_osv(('Error'), ('Insert interval number and unit'))

    def create_cron_products_stock(self):
        if self.import_categories_interval_time and self.import_categories_interval_units:
            cron_name = 'magento_stock' + str(self.id)
            exist = self.env['ir.cron'].search([('name', '=', cron_name)])
            function_name = 'cron_stock_magento'
            if self.incremental_imports:
                function_name += '_incremental'
            vals = {
                'name': 'magento_stock',
                'interval_number': int(self.import_products_stock_interval_time),
                'interval_type': self.import_products_stock_interval_units,
                'model': 'magento.sync',
                'numbercall': -1,
                'function': function_name
            }
            if not exist:
                self.env['ir.cron'].create(vals)
            else:
                exist.write(vals)
        else:
            raise osv.except_osv(('Error'), ('Insert interval number and unit'))

    def create_cron_sales_orders(self):
        if self.import_categories_interval_time and self.import_categories_interval_units:
            cron_name = 'magento_sale_order' + str(self.id)
            exist = self.env['ir.cron'].search([('name', '=', cron_name)])
            function_name = 'cron_sale_order_magento'
            if self.incremental_imports:
                function_name += '_incremental'
            vals = {
                'name': cron_name,
                'active': True,
                'interval_number': int(self.import_sales_orders_interval_time),
                'interval_type': self.import_sales_orders_interval_units,
                'numbercall': -1,
                'model': 'magento.sync',
                'function': function_name,
                'priority': 2,
                'args': (self.id,)
            }
            if not exist:
                self.env['ir.cron'].create(vals)
            else:
                exist.write(vals)
        else:
            raise osv.except_osv(('Error'), ('Insert interval number and unit'))

    def manual_sync_product(self):
        magento_sync_obj = self.env['magento.sync'].search([("magento_web_shop_ids.id", "=", self.id)])
        magento_sync_obj.single_product(self.manual_import_product_magento_id)


    def manual_sync_sale_order(self):
        magento_sync_obj = self.env['magento.sync'].search([("magento_web_shop_ids.id", "=", self.id)])
        magento_sync_obj.sync_single_sale_order(self.manual_import_sale_order_magento_id)