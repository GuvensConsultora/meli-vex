from odoo import api, fields, models

class VexProductAttribute(models.Model):
    _inherit         = "product.attribute"

    meli_code = fields.Char('Código ML')
    server_meli = fields.Boolean('server_meli')
    instance_id = fields.Many2one('vex.instance', string='Instance id')

class VexProductAttributeValue(models.Model):
    _inherit         = "product.attribute.value"

    instance_id = fields.Many2one('vex.instance', string='Instance id')