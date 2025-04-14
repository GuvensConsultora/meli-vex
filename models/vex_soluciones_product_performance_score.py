from odoo import models, fields, api

class ProductPerformanceScore(models.Model):
    _name = "product.performance.score"
    _description = "Puntaje de rendimiento del producto"

    product_tmpl_id = fields.Many2one("product.template", string="Producto", ondelete="cascade")
    name = fields.Char(string="Descripción")
    sub_performance_score = fields.Integer(string="Puntaje de Rendimiento")
    sub_performance_level = fields.Char(string="Nivel de Rendimiento")