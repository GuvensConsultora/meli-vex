from odoo import models, fields, api


class PriceEvolutionData(models.Model):
    _name = 'vex.soluciones.price.evolution.data'
    _description = 'Price Evolution Data'

    product_id = fields.Many2one('product.template', string='Product', required=True)
    change_date = fields.Datetime(string="Change Date", default=fields.Datetime.now, required=True)
    old_price = fields.Float(string="Old Price", required=True)
    new_price = fields.Float(string="New Price", required=True)
