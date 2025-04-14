from odoo import fields, models, api

class VexSolucionesSku(models.Model):
    _name="vex.sku"

    name = fields.Char('name')
    instance_id = fields.Many2one('vex.instance', string='Instance id')