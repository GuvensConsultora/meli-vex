from odoo import models, fields

class VexSolucionesTrends(models.Model):
    _name = 'vex_soluciones.trends'
    _description = 'Trends'

    name = fields.Char(string='Name', required=True)  # Nombre
    popularity = fields.Integer(string='Popularity')  # Popularidad
    category = fields.Char(string='Category')  # Categoría
    trend_score = fields.Float(string='Trend Score')  # Puntaje de tendencia
    created_date = fields.Datetime(string='Created Date')  # Fecha de creación