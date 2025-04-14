import requests
from odoo import models, fields, api
import logging

# Configurar el logger
_logger = logging.getLogger(__name__)

class VexSolucionesMarketCategory(models.Model):
    _name = 'vex.category'
    _description = 'Category'

    name = fields.Char('Pais')
    codigo_ml = fields.Char('Codigo ML')
    description = fields.Char('Categoria')
    publications_count =  fields.Integer('Cantidad Publicaciones')
    count_sellers =  fields.Integer('Cantidad de Vendedores')
    participation =  fields.Char('Participacion')
    units_sold =  fields.Integer('Unidades Vendidas')
    billing =  fields.Float('Facturacion %')
    instance_id = fields.Many2one('vex.instance', string="Instancia")
    trending_keyword_ids = fields.One2many(
        "vex.category.trending.keyword", 
        "category_id", 
        string="Palabras más buscadas"
    )

    def action_open_owl(self):
        return {
        "type": "ir.actions.client",
        "tag": "mi_componente_owl",
        "params": {"category_id": self.id},  # Asegúrate de pasar el ID aquí
    }
    
    @api.model
    def consumir_api_categorias_mercado_libre(self):
        for instance in self.env['vex.instance'].search([]):
            site_id = instance.meli_country

            url = f"https://api.mercadolibre.com/sites/{site_id}/categories"

            response = requests.get(url)

            if response.status_code == 200:
                categories = response.json()
                for item in categories:
                    obj={
                        'description': item['name'],
                        'codigo_ml':item['id'],
                        'instance_id': instance.id
                    }

                    category_exist = self.env['vex.category'].search([('description','=', item['name']),('instance_id','=', instance.id)])
                    if not category_exist:
                        new_categories = self.env['vex.category'].create(obj)

            else:
                print(f"Error {response.status_code}: {response.text}")

    @api.model
    def actualizar_publicaciones_categoria(self):
        for instance in self.env['vex.instance'].search([('store_type','=','mercadolibre')]):
            site_id = instance.meli_country
            category_ids = self.env['vex.category'].search([])
            for category in category_ids:
                CATEGORY_ID = category.codigo_ml
                URL = f"https://api.mercadolibre.com/sites/{site_id}/search?category={CATEGORY_ID}"

                response = requests.get(URL)

                if response.status_code == 200:
                    data_response = response.json()
                    # print(data_response["paging"]["total"])

                    obj = {
                        'publications_count': data_response["paging"]["total"]
                    }
                
                    category.write(obj)

                else:
                    print(f"Error {response.status_code}: {response.text}")

    @api.model
    def actualizar_cantidad_vendedores_categoria(self):
        for instance in self.env['vex.instance'].search([('store_type','=','mercadolibre')]):
            site_id = instance.meli_country
            category_ids = self.env['vex.category'].search([])
            for category in category_ids:
                CATEGORY_ID = category.codigo_ml
                URL = f"https://api.mercadolibre.com/sites/{site_id}/search?category={CATEGORY_ID}&limit=50"  # Ajusta el límite según necesidad

                response = requests.get(URL)

                if response.status_code == 200:
                    data_response = response.json()

                    sellers_ids = set(item["seller"]["id"] for item in data_response["results"])

                    obj = {
                        'count_sellers': len(sellers_ids)
                    }

                    category.write(obj)

                else:
                    print(f"Error {response.status_code}: {response.text}")

    @api.model
    def actualizando_participacion_categoria(self):
        for instance in self.env['vex.instance'].search([('store_type','=','mercadolibre')]):
            site_id = instance.meli_country
            category_ids = self.env['vex.category'].search([])
        
            datos_categorias = {}

            # PRIMERO: Obtener productos por categoría
            for categoria in category_ids:
                category_id = categoria.codigo_ml
                category_name = categoria.description

                url_productos = f"https://api.mercadolibre.com/sites/{site_id}/search?category={category_id}"
                response = requests.get(url_productos).json()

                cantidad_productos = response.get("paging", {}).get("total", 0)
                datos_categorias[category_name] = cantidad_productos

            # SEGUNDO: Calcular total de productos
            total_productos = sum(datos_categorias.values())

            # TERCERO: Calcular participación porcentual (usando un total FIJO)
            participacion = {k: (v / total_productos * 100) if total_productos > 0 else 0 for k, v in datos_categorias.items()}
            print(participacion)

            for cat_id in category_ids:
                for categoria, porcentaje in participacion.items():
                    print(categoria)
                    print(round(porcentaje,2))

                    if categoria == cat_id.description:
                        obj = {
                            'participation': f"{round(porcentaje, 2)}%"
                        }

                        cat_id.write(obj)

    @api.model
    def palabras_mas_buscadas(self):
        for instance in self.env['vex.instance'].search([('store_type','=','mercadolibre')]):
            instance.get_access_token()
            site_id = instance.meli_country
            access_token = instance.access_token
            category_ids = self.env['vex.category'].search([])
        
            for categoria in category_ids:
                category_id = categoria.codigo_ml

                url = f"https://api.mercadolibre.com/trends/{site_id}/{category_id}"
                headers = {
                    "Authorization": f"Bearer {access_token}"
                }

                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    trends = response.json()

                    for item in trends:
                        print(item)

                        obj = {
                            'category_id': categoria.id,
                            'keyword': item['keyword'],
                        }
                        write_keyword = self.env['vex.category.trending.keyword'].search([('keyword','=', item['keyword'])])
                        if not write_keyword: 
                            self.env['vex.category.trending.keyword'].create(obj)
                else:
                    trends = f"Error {response.status_code}: {response.text}"