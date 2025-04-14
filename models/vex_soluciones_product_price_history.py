from odoo import models, fields, api

class ProductPriceHistory(models.Model):
    _name = 'vex.soluciones.product.price.history'
    _description = 'Historical Product Prices'
    _order = 'date_change desc'  # Ordenar por fecha de cambio

    product_id = fields.Many2one('product.template', string="Product", required=True, ondelete="cascade")
    old_price = fields.Float(string="Old Price")
    new_price = fields.Float(string="New Price", required=True)
    date_change = fields.Datetime(string="Change Date", default=fields.Datetime.now, required=True)
