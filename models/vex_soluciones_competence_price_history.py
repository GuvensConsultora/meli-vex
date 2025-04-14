from odoo import models, fields

class CompetencePriceHistory(models.Model):
    _name = 'vex.soluciones.competence.price.history'
    _description = 'Competence Price History'
    _order = 'date_change desc'  # Ordenar por fecha de cambio

    product_id = fields.Many2one('product.template', string="Product", required=True)
    competitor_name = fields.Char(string="Competitor", required=True)
    competitor_price = fields.Float(string="Competitor Price", required=True)
    date_change = fields.Datetime(string="Change Date", default=fields.Datetime.now, required=True)
