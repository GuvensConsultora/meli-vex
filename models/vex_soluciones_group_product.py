from odoo import models, fields, api

class VexGroup(models.Model):
    _name = 'vex.group_product'

    name = fields.Char('Name')
    url = fields.Char('Url')
    num_publication = fields.Char('Publication')
    product_id = fields.Many2one('product.template', string='Product')
    image = fields.Binary('image')
    price = fields.Float('price')
    export_to_meli = fields.Boolean('export_to_meli', default=True)
    categ_id = fields.Many2one('product.category', string='ML Category')
    meli_category_code = fields.Char('Category Code ML')
    action_export = fields.Selection([
        ('edit', 'Edition'),
        ('create', 'Creation')
    ], string='Action', default="create", readonly=True)
    quantity = fields.Integer('Quantity')
    sku_id = fields.Many2one('vex.sku', string='sku')
    instance_id = fields.Many2one('vex.instance', string='Instance id')