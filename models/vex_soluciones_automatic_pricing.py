from odoo import models, fields, api
from datetime import datetime

class VexAutomaticPricing(models.Model):
    #vex_price_evolution_data
    _name = 'vex.automatic.pricing'  # Reemplaza con el nombre de tu modelo
    _description = 'Modelo para la automatización de precios' 

    pricing_strategy = fields.Selection([
        ('cheapest', 'Contra la publicación más barata del grupo'),
        ('most_expensive', 'Contra la publicación más cara del grupo'),
        ('average', 'Contra el precio promedio del grupo'),
    ], string="Configura tu precio automático")
    product_id = fields.Many2one('product.template', string="Producto Asociado", required=True)
    competitors_data = fields.Json(string="Datos de Competencia", help="Contiene name, url, price y last_updated")
    is_rule_active = fields.Boolean(string="¿Regla Activa?", default=False)
    minimum_price_limit = fields.Float(string="Límite de Precio Mínimo")
    maximum_price_limit = fields.Float(string="Límite de Precio Máximo")

    @api.model
    def supervise_competitors(self):
        """
        Método para supervisar los productos de la competencia.
        Define si se ejecuta one-time, real-time o por cron.
        """
        # Obtén los datos JSON del campo competitors_data
        for record in self:
            competitors = record.competitors_data
            if not competitors:
                continue
            
            # Ejemplo de procesamiento de datos
            for competitor in competitors:
                name = competitor.get('name')
                url = competitor.get('url')
                price = competitor.get('price')
                last_updated = competitor.get('last_updated')
                
                # Agregar lógica de actualización aquí...
                self._update_competitor_data(name, url, price)

    def _update_competitor_data(self, name, url, price):
        """
        Actualiza los datos del competidor con lógica personalizada.
        """
        # Ejemplo de actualización
        now = datetime.now()
        self.competitors_data = [
            {
                'name': name,
                'url': url,
                'price': price,
                'last_updated': now.strftime("%Y-%m-%d %H:%M:%S"),
            }
        ]
