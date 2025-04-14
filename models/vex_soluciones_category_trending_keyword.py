from odoo import models, fields, api

class VexCategoryTrendingKeyword(models.Model):
    _name = "vex.category.trending.keyword"
    _description = "Palabras más buscadas por categoría"
    _rec_name = "keyword"
   
    category_id = fields.Many2one(
        "vex.category", 
        string="Categoría", 
        ondelete="cascade",
        help="Categoría asociada a la palabra clave"
    )

    keyword = fields.Char(
        string="Palabra clave", 
        required=True,
        help="Palabra más buscada en la categoría"
    )