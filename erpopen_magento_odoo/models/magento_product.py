from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

import odoo.addons.decimal_precision as dp


class ProductProduct(models.Model):
    _inherit = 'product.product'

    magento_id = fields.Integer()
    magento_sync = fields.Boolean('Sync with magento')

    @api.multi
    def write(self, vals):
        # magento_settings = self.magento_web_shop_ids
        #
        # if magento_settings and magento_settings.enable_syncing_to_magento and ('magento_import' not in vals or not vals['magento_import']) and (self.magento_sync or ('magento_sync' in vals and vals['magento_sync'])):
        #     self.export_update_product()
        return super(ProductProduct, self).write(vals)

    def export_update_stock(self):
        magento_settings = self.magento_web_shop_ids

        if magento_settings and magento_settings.enable_syncing_to_magento:
            socket, session = self.env['magento.sync'].connection()
            product_ids = self

            for product in product_ids:
                parameter = []
                datas = {}
                stock_data = {}
                product_uom_qty_ids = self.env['stock.quant'].search([('product_id', '=', int(product.id))])
                if product_uom_qty_ids:
                    sum = 0
                    for product_qty in product_uom_qty_ids:
                        sum += product_qty.qty
                    stock_data['qty'] = str(sum)
                else:
                    stock_data['qty'] = '0'
                datas['stock_data'] = stock_data

                if product.magento_id:
                    magento_stores = self.env['magento.store'].search([('id', '!=', -1)])
                    for magento_store in magento_stores:
                        parameter = []
                        parameter.append(str(product.magento_id))
                        parameter.append(datas)
                        parameter.append(magento_store.magento_id)
                        parameter.append('id')
                        id = socket.call(session, "catalog_product.update", parameter)
                else:
                    parameter = []
                    parameter.append(str(product.magento_type.name))  # product type
                    parameter.append(str(product.magento_set.magento_id))  # product attribute type id
                    parameter.append(str(product.default_code))  # product sku
                    parameter.append(datas)  # product data
                    parameter.append('0')
                    product.magento_id = socket.call(session, "catalog_product.create", parameter)

    def export_update_product(self):
        magento_settings = self.magento_web_shop_ids

        if magento_settings and magento_settings.enable_syncing_to_magento:
            socket, session = self.env['magento.sync'].connection()
            product_ids = self
            for product in product_ids:
                parameter = []
                datas = {}
                stock_data = {}
                product_uom_qty_ids = self.env['stock.quant'].search([('product_id', '=', int(product.id))])
                if product_uom_qty_ids:
                    sum = 0
                    for product_qty in product_uom_qty_ids:
                        sum += product_qty.qty
                    stock_data['qty'] = str(sum)
                else:
                    stock_data['qty'] = '0'
                datas['stock_data'] = stock_data

                if product.magento_status:
                    datas['status'] = str('1')
                else:
                    datas['status'] = str('2')
                if not product.active:
                    datas['status'] = str('2')
                if product.magento_visibility:
                    datas['visibility'] = str('4')
                if product.magento_special_price:
                    datas['price'] = product['magento_special_price']  # weird mapping for sanitairkamer
                if product.magento_special_from_date:
                    datas['special_from_date'] = str(product.magento_special_from_date)
                if product.magento_special_to_date:
                    datas['special_to_date'] = str(product.magento_special_to_date)
                if product.magento_meta_title:
                    datas['meta_title'] = str(product.magento_meta_title)
                if product.magento_meta_keyword:
                    datas['meta_keyword'] = str(product.magento_meta_keyword)
                if product.magento_meta_description:
                    datas['meta_description'] = str(product.magento_meta_description)
                if product.magento_custom_design:
                    datas['custom_design'] = str(product.magento_custom_design)
                if product.name:
                    datas['name'] = str(product.name)
                if product.list_price:
                    datas['special_price'] = str(product.list_price)  # weird mapping for sanitairkamer
                if product.magento_description:
                    datas['description'] = str(product.magento_description)
                datas['websites'] = ['1', '2']
                category_ids = []
                for category in product.magento_category_ids:
                    if category.magento_id:
                        category_ids.append(str(category.magento_id))
                if len(category_ids) > 0:
                    datas['category_ids'] = category_ids

                if product.magento_id:
                    magento_stores = self.env['magento.store'].search([('id', '!=', -1)])
                    for magento_store in magento_stores:
                        parameter = []
                        parameter.append(str(product.magento_id))
                        parameter.append(datas)
                        parameter.append(magento_store.magento_id)
                        parameter.append('id')
                        id = socket.call(session, "catalog_product.update", parameter)
                    parameter = []
                    parameter.append(str(product.magento_id))
                    parameter.append(datas)
                    parameter.append("")
                    parameter.append('id')
                    id = socket.call(session, "catalog_product.update", parameter)
                else:
                    parameter = []
                    parameter.append(str(product.magento_type.name))  # product type
                    parameter.append(str(product.magento_set.magento_id))  # product attribute type id
                    parameter.append(str(product.default_code))  # product sku
                    parameter.append(datas)  # product data
                    parameter.append('0')
                    product.magento_id = socket.call(session, "catalog_product.create", parameter)

                existing_images = socket.call(session, "catalog_product_attribute_media.list", [str(product.magento_id)])
                existing_images_urls = []
                for existing_image in existing_images:
                    existing_images_urls.append(existing_image['url'])

                for file in product.magento_images_ids:
                    media_param = []
                    media_param.append(str(product.magento_id))

                    medias = {}
                    medias_list = {}
                    medias_list['content'] = str(file.datas)
                    medias_list['mime'] = str(file.mimetype)
                    medias_list['name'] = str(file.name)

                    medias['file'] = medias_list
                    if file.description:
                        medias['label'] = str(file.description)
                    medias['position'] = str(file.sortable)
                    medias['exclude'] = '0'

                    media_param.append(medias)
                    media_param.append('1')
                    media_param.append('slxxmckdoe')
                    if file.url in existing_images_urls:
                        media_param[2] = media_param[1]
                        image_name = ""
                        for existing_image in existing_images:
                            if existing_image['url'] == file.url:
                                media_param[1] = existing_image['file']
                        magento_stores = self.env['magento.store'].search([('id', '!=', -1)])
                        for magento_store in magento_stores:
                            media_param[3] = str(magento_store.magento_id)
                            media_result = socket.call(session, "catalog_product_attribute_media.update",
                                                       media_param)
                        media_param[3] = '0'
                        media_result = socket.call(session, "catalog_product_attribute_media.update",
                                                   media_param)
                    else:
                        media_result = socket.call(session, "catalog_product_attribute_media.create",
                                               media_param)
                        existing_images = socket.call(session, "catalog_product_attribute_media.list", [str(product.magento_id)])
                        for existing_image in existing_images:
                            if media_result == existing_image['file']:
                                file.write({'url': existing_image['url']})
                                break

    min_quantity = fields.Integer(
        'Min. Quantity', default=1,
        help="For the rule to apply, bought/sold quantity must be greater "
             "than or equal to the minimum quantity specified in this field.\n"
             "Expressed in the default unit of measure of the product.")
    base = fields.Selection([
        ('list_price', 'Public Price'),
        ('standard_price', 'Cost'),
        ('pricelist', 'Other Pricelist')], "Based on",
        default='list_price',
        help='Base price for computation.\n'
             'Public Price: The base price will be the Sale/public Price.\n'
             'Cost Price : The base price will be the cost price.\n'
             'Other Pricelist : Computation of the base price based on another Pricelist.')
    price_surcharge = fields.Float(
        'Price Surcharge', digits=dp.get_precision('Product Price'),
        help='Specify the fixed amount to add or substract(if negative) to the amount calculated with the discount.')
    price_discount = fields.Float('Price Discount', default=0, digits=(16, 2))
    price_round = fields.Float(
        'Price Rounding', digits=dp.get_precision('Product Price'),
        help="Sets the price so that it is a multiple of this value.\n"
             "Rounding is applied after the discount and before the surcharge.\n"
             "To have prices that end in 9.99, set rounding 10, surcharge -0.01")
    price_min_margin = fields.Float(
        'Min. Price Margin', digits=dp.get_precision('Product Price'),
        help='Specify the minimum amount of margin over the base price.')
    price_max_margin = fields.Float(
        'Max. Price Margin', digits=dp.get_precision('Product Price'),
        help='Specify the maximum amount of margin over the base price.')
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        readonly=True, related='pricelist_id.currency_id', store=True)
    compute_price = fields.Selection([
        ('fixed', 'Fix Price'),
        ('percentage', 'Percentage (discount)')], index=True, default='fixed')
    fixed_price = fields.Float('Fixed Price', digits=dp.get_precision('Product Price'))
    percent_price = fields.Float('Percentage Price')
    price = fields.Char(
        'Price', compute='_get_pricelist_item_name_price',
        help="Explicit rule name for this pricelist line.")

    @api.constrains('price_min_margin', 'price_max_margin')
    def _check_margin(self):
        if any(item.price_min_margin > item.price_max_margin for item in self):
            raise ValidationError(_('Error! The minimum margin should be lower than the maximum margin.'))
        return True

    @api.one
    @api.depends('compute_price', 'fixed_price', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        if self.compute_price == 'fixed':
            self.price = ("%s %s") % (self.fixed_price, self.pricelist_id.currency_id.name)
        elif self.compute_price == 'percentage':
            self.price = _("%s %% discount") % (self.percent_price)
        else:
            self.price = _("%s %% discount and %s surcharge") % (abs(self.price_discount), self.price_surcharge)

    @api.onchange('compute_price')
    def _onchange_compute_price(self):
        if self.compute_price != 'fixed':
            self.fixed_price = 0.0
        if self.compute_price != 'percentage':
            self.percent_price = 0.0
        if self.compute_price != 'formula':
            self.update({
                'price_discount': 0.0,
                'price_surcharge': 0.0,
                'price_round': 0.0,
                'price_min_margin': 0.0,
                'price_max_margin': 0.0,
            })

    def get_fee(self, order_price):
        if self.compute_price == 'fixed':
            return self.fixed_price
        elif self.compute_price == 'percentage':
            return (self.percent_price / 100) * order_price
