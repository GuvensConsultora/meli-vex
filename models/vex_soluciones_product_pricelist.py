from odoo import api, fields, models

class VexProductPricelist(models.Model):
    _inherit         = "product.pricelist"

    meli_code = fields.Char('Código ML')
    server_meli = fields.Boolean('server_meli')

class VexProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    meli_id = fields.Char('MELI ID')