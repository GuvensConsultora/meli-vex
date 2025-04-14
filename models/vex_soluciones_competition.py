from odoo import models, fields

class VexSolucionesCompetition(models.Model):
    _name = 'vex_soluciones.competition'
    _description = 'Competition - Mercado Libre'

    item_id = fields.Char(string='Item ID', required=True)  # ID del producto en Mercado Libre
    current_price = fields.Float(string='Current Price')  # Precio actual de la publicación
    price_to_win = fields.Float(string='Price to Win')  # Precio mínimo para ganar en la competencia
    status = fields.Selection([
        ('winning', 'Winning'),
        ('competing', 'Competing'),
        ('losing', 'Losing')
    ], string='Status')  # Estado de la publicación en la competencia
    visit_share = fields.Selection([
        ('maximum', 'Maximum'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ], string='Visit Share')  # Nivel de exposición en visitas
    competitors_sharing_first_place = fields.Integer(string='Competitors Sharing First Place')  # Número de competidores en primer lugar
    catalog_product_id = fields.Char(string='Catalog Product ID')  # ID del producto en el catálogo
