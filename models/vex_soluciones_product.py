# Importaciones de la biblioteca estándar
import base64
import logging
import requests
import openai
from bs4 import BeautifulSoup
# from rembg import remove
from PIL import Image 
from io import BytesIO

# Importaciones de terceros (bibliotecas de manejo de datos y gráficos)
from prophet import Prophet
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import plotly.graph_objects as go
import plotly.offline as pyo
from datetime import datetime, timedelta

# Importaciones específicas de Odoo
from odoo import fields, models, api
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

MERCADO_LIBRE_URL = "https://api.mercadolibre.com"
WALMART_API_URL = "https://marketplace.walmartapisSANDBOX.com/v3/price"



_logger = logging.getLogger(__name__)
class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

   # contenido_html = "<h1>Contenido HTML</h1><p>Este es el contenido de tu archivo HTML.</p>"
    contenido_html = fields.Html(string='Contenido HTML')

    meli_code = fields.Char('Code ML')
    server_meli = fields.Boolean('Server meli')
    export_to_meli = fields.Boolean('Export to MELI')
    ml_reference = fields.Char('Reference ML')
    ml_publication_code = fields.Char('MELI Publication ID')
    meli_category_code = fields.Char('Codigo Categoría ML')
    
    sku_id = fields.Many2one('vex.sku', string='sku')
    group_ids = fields.One2many('vex.group_product', 'product_id', string='Group', compute='_compute_group_ids')
    meli_status = fields.Char('Status ML')
    listing_type_id = fields.Char('Listing Type')
    condition = fields.Char('Condition')
    permalink = fields.Char('Permalink')
    thumbnail = fields.Char('Thumbnail')
    buying_mode = fields.Char('Buying Mode')
    inventory_id = fields.Char('MELI Inventory ID')
    is_package = fields.Boolean('Is a Package?')
    #product_unit_ids = fields.Many2many('product.template.units', string='Productos Unitarios')
    product_unit_ids = fields.One2many('product.template.units', 'product_tmpl_id', string='product_unit')
    action_export = fields.Selection([
        ('edit', 'Edition'),
        ('create', 'Creation')
    ], string='Action export', default="create")
    
    attachment_id = fields.Many2one('ir.attachment', string='Attachment')
    instance_id = fields.Many2one('vex.instance', string='instance') #Agregamos valor de instancia al producto
    stock_type = fields.Char() #Para stock

    price_score = fields.Char(string="Price Score")

    evolution_data_ids = fields.One2many(
        'vex.soluciones.price.evolution.data', 'product_id', string='Price Evolution Data'
    )

    # competence_price_history_ids = fields.One2many( Ya no se usa
    #     'vex.soluciones.competence.price.history', 'product_id', string="Competence Price History"
    # )

    automatic_pricing_ids = fields.One2many(
        'mercado.libre.product', 'product_id',
        string="Automatic Pricing Rules",
        domain=[('data_type', '=', 'competence')]  # Filtrar solo los registros con data_type = 'competence'
    )



    #SUPLEFIT_LOGIC -- START

    warehouse_location = fields.Selection(
        [('bodega_1', 'Bodega 1'), ('bodega_2', 'Bodega 2')],
        string="Bodega",
        compute="_compute_warehouse_location",
        store=True
    )

    @api.depends('name')
    def _compute_warehouse_location(self):
        for product in self:
            if product.name and " Eg" in product.name:
                product.warehouse_location = 'bodega_2'
            else:
                product.warehouse_location = 'bodega_1'

    #SUPLEFIT_LOGIC -- END


    #MODELS FOR WALMART

    upc = fields.Char(string="UPC")
    walmart_sku = fields.Char(string="SKU")
    walmart_wpid = fields.Char(string="Walmart WPID")
    walmart_product_type = fields.Char(string="Product Type")
    walmart_shelves = fields.Text(string="Shelves")
    walmart_published_status = fields.Char(string="Published Status")
    walmart_lifecycle_status = fields.Char(string="Lifecycle Status")

    #NECESITAMOS UN STORETYPE AQUI ---Listo
    store_type = fields.Selection([
        ('mercadolibre', 'Mercado Libre'),
        ('walmart', 'Walmart')
    ], string="Store Type")


    #Maestro

    parent_product = fields.Boolean(string="This is a parent product?")
    children_products_data = fields.Json(string="Children Products Data")

    # Variables para diferentes precios en diferentes tiendas
    walmart_price = fields.Float(string="Walmart Price")
    amazon_price = fields.Float(string="Amazon Price")
    mercado_libre_price = fields.Float(string="Mercado Libre Price")
    shopify_price = fields.Float(string="Shopify Price")


    date_filter_start = fields.Date(string="Start Date")

    date_from = fields.Datetime('Date from')
    date_to = fields.Datetime('Date to')

    
    performance_score = fields.Integer(string="Puntaje de Rendimiento")
    performance_level = fields.Char(string="MELI Score")
    performance_score_ids = fields.One2many("product.performance.score", 'product_tmpl_id', string="Puntajes de rendimiento")
    description_product = fields.Html(string='Descripción')
    description_optimized = fields.Text(string='Descripción Optimizada')
    
    request_prompt = fields.Text(
        "Solicitud para OpenAI",
        help="Escribe qué quieres que haga OpenAI con la descripción del producto."
    )

    image_no_bg = fields.Binary("Imagen sin fondo", help="Imagen del producto con fondo blanco.")

    market_fee = fields.Monetary(string='MELI fee')

    competitor_price_history_ids = fields.One2many(
        'mercado.libre.product.compared',
        compute='_compute_competitor_price_history',
        string="Historial de Precios de la Competencia",
        store=False  # Solo visualización
    )
    # def remove_background_odoo(self):
    #     """ 
    #     Elimina el fondo de la imagen principal (image_1920) y la guarda en image_no_bg
    #     """
    #     if not self.image_1920:
    #         _logger.warning(f"⚠ No hay imagen en el producto: {self.name}")
    #         return

    #     try:
    #         # Convertir la imagen Base64 de Odoo a una imagen PIL
    #         image_data = base64.b64decode(self.image_1920)
    #         image = Image.open(BytesIO(image_data))

    #         # Remover el fondo
    #         img_no_bg = remove(image)

    #         # Crear una nueva imagen con fondo blanco
    #         new_image = Image.new("RGBA", img_no_bg.size, (255, 255, 255, 255))
    #         new_image.paste(img_no_bg, mask=img_no_bg.split()[3])

    #         # Convertir a RGB (sin transparencia)
    #         final_image = new_image.convert("RGB")

    #         # Guardar la imagen en memoria como PNG
    #         img_buffer = BytesIO()
    #         final_image.save(img_buffer, format="PNG")

    #         # Convertir la imagen a Base64 y guardar en `image_no_bg`
    #         self.image_no_bg = base64.b64encode(img_buffer.getvalue()).decode()

    #         _logger.info(f"✅ Fondo eliminado correctamente en el producto: {self.name}")

    #     except Exception as e:
    #         _logger.error(f"❌ Error eliminando fondo en {self.name}: {e}")

    # Función para optimizar la descripción usando OpenAI
    def action_optimize_description(self):
        for record in self:
            # Verificar si el campo request_prompt tiene contenido
            if record.request_prompt:
                try:
                    # Configura tu API Key de OpenAI
                    OPENAI_API_KEY = "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"
                    client = openai.OpenAI(api_key=OPENAI_API_KEY)

                    # Crear el prompt combinando la descripción y lo que el usuario escribió en request_prompt
                    prompt_text = f"{record.request_prompt}: {record.description_product}"
                    response = client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt_text}]
                    )

                    # Obtener la descripción optimizada y actualizar el campo description
                    optimized_description = response.choices[0].message.content
                    # Limpiar las etiquetas HTML usando BeautifulSoup
                    cleaned_description = BeautifulSoup(optimized_description, "html.parser").get_text()
                    record.description_optimized = cleaned_description  # Actualiza el campo description con el texto optimizado
                    return True

                except Exception as e:
                    # Manejo de errores si ocurre un problema con la API
                    return f"Error: {e}"
            else:
                return "Error: No hay un prompt proporcionado."

    @api.model
    def fetch_meli_description(self):
        for instance in self.env['vex.instance'].search([('store_type','=','mercadolibre')]):
            #ACCESS_TOKEN = "APP_USR-7132845339561770-022418-fd36a16f40d799a348eddf152a193077-306833514"
            instance.get_access_token()
            ACCESS_TOKEN = instance.access_token
            product_ids = self.env['product.template'].search([('store_type','=','mercadolibre')])

            for product in product_ids:
                ITEM_ID = product.ml_publication_code
            
                url = f"https://api.mercadolibre.com/items/{ITEM_ID}/description"

                headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    data_response = response.json()

                    obj = {
                        'description_product': data_response['plain_text']
                    }

                    write_register = product.write(obj)
                    if write_register:
                        _logger.info("Producto actualizado con éxito: %s", product.name)
                    else:
                        _logger.info("No se pudo actualizar el registro: %s", product.name)
                else:
                    print(f"Error {response.status_code}: {response.text}")

    def _compute_competitor_price_history(self):
        for product in self:
            ml_products = self.env['mercado.libre.product'].search([
                ('product', '=', product.id)
            ])
            compared = self.env['mercado.libre.product.compared'].search([
                ('parent_id', 'in', ml_products.ids)
            ])
            product.competitor_price_history_ids = compared

    @api.model
    def consumir_score_performance(self):   
        for instance in self.env['vex.instance'].search([('store_type','=','mercadolibre')]):
            instance.get_access_token()
            access_token = instance.access_token
            product_ids = self.env['product.template'].search([('store_type','=','mercadolibre'),('instance_id', '=', instance.id)])

            for product in product_ids:
                item_id = product.ml_publication_code

                # URL del endpoint
                url = f"https://api.mercadolibre.com/item/{item_id}/performance"

                # Cabeceras con el token de autorización
                headers = {
                    "Authorization": f"Bearer {access_token}"
                }

                # Realizar la petición GET
                response = requests.get(url, headers=headers)

                # Verificar el código de estado de la respuesta
                if response.status_code == 200:
                    data = response.json()
                
                    obj={
                        'performance_score': data['score'],
                        'performance_level': str(round(data['score'])) + ' / 100 ' + data['level'],
                    }

                    write_register = product.write(obj)
                    if write_register:
                        _logger.info("Producto actualizado con éxito: %s", product.name)
                    else:
                        _logger.info("No se pudo actualizar el registro: %s", product.name)

                    for bucket in data['buckets']:
                        print("================== BUCKETS ===========================")
                        sub_score = int(bucket.get('score', 0))
                        if sub_score >= 90:
                            sub_performance_level = "Excellent"
                        elif sub_score >= 75:
                            sub_performance_level = "Good"
                        elif sub_score >= 50:
                            sub_performance_level = "Average"
                        else:
                            sub_performance_level = "Poor"

                        obj_bucket = {
                            'product_tmpl_id': product.id,
                            'name': bucket.get('title', 'Sin nombre'),
                            'sub_performance_score': int(bucket.get('score', 0)),
                            'sub_performance_level': str(round(bucket['score'])) + ' / 100 ' + sub_performance_level
                        }
                        sub_score_product = self.env['product.performance.score'].create(obj_bucket)

                        if sub_score_product:
                            _logger.info("Se crearon los buckets score satisfactoriamente: %s", product.name)
                        else:
                            _logger.info("No se pudo crear crear los buckets score: %s", product.name)
                        
                        for variable in bucket['variables']:
                            print("============== VARIABLES ===================")
                            variable_score = int(variable.get('score', 0))
                            if variable_score >= 90:
                                variable_performance_level = "Excellent"
                            elif variable_score >= 75:
                                variable_performance_level = "Good"
                            elif variable_score >= 50:
                                variable_performance_level = "Average"
                            else:
                                variable_performance_level = "Poor"

                            obj_values = {
                                'product_tmpl_id': product.id,
                                'name':variable['title'],
                                'sub_performance_score': variable['score'],
                                'sub_performance_level': str(round(variable['score'])) + ' / 100 ' + variable_performance_level
                            }

                            sub_values_product = self.env['product.performance.score'].create(obj_values)
                            if sub_values_product:
                                _logger.info("Variables de score creados satisfactoriamente: %s", product.name)
                            else:
                                _logger.info("No se pudo crear las variables: %s", product.name) 
                else:
                    print(f"Error {response.status_code}: {response.text}")
    
    @api.model
    def create(self, vals):        

        product = super(InheritProductTemplate, self).create(vals)
        if vals.get('image_1920'):
            self.create_or_update_attachment(product, vals.get('image_1920'))

        return product
    
    def update_ecommerce_prices(self, modified_prices):
        for product in self:
            if 'walmart_price' in modified_prices:
                # Logic to update Walmart price
                _logger.info(f"Updating Walmart price for product {product.id} to {modified_prices['walmart_price']}")
                if product.upc:
                    _logger.info(f"Product {product.id} has UPC: {product.upc}")
                    _logger.info('Linkeando producto por walmart upc')
                    #Buscamos un producto que tenga el UPC y store type = walmart
                    # update_product_price_walmar() Lllamamos a la ejecucion de la actualizacion

                elif product.store_type == 'walmart':
                    pass
                    #Logic to update a product that is native from walmart


            if 'amazon_price' in modified_prices:
                # Logic to update Amazon price
                _logger.info(f"Updating Amazon price for product {product.id} to {modified_prices['amazon_price']}")
                if product.upc:
                    _logger.info(f"Product {product.id} has UPC: {product.upc}")

            if 'mercado_libre_price' in modified_prices:
                # Logic to update Mercado Libre price

                if product.store_type == 'mercadolibre':
                    self.update_mercado_libre_price(product, modified_prices['mercado_libre_price'])
                    

            if 'shopify_price' in modified_prices:
                # Logic to update Shopify price
                _logger.info(f"Updating Shopify price for product {product.id} to {modified_prices['shopify_price']}")
                if product.upc:
                    _logger.info(f"Product {product.id} has UPC: {product.upc}")



    def update_mercado_libre_price(self, product, new_price):
        _logger.info(f"Updating Mercado Libre price for product {product.id} to {new_price}")
        access_token = product.instance_id.access_token
        self.update_product_price_mercadolibre(item_id=product.meli_code,access_token=access_token,new_price=new_price)
        


    def write(self, vals):
        # Logic for updating prices for different marketplaces
        price_fields = ['walmart_price', 'amazon_price', 'mercado_libre_price', 'shopify_price']
        modified_prices = {field: vals[field] for field in price_fields if field in vals and vals[field] != 0}

        _logger.info("Logic for modified_prices")

        if modified_prices:
            _logger.info(f"The following prices are being modified: {modified_prices}")
            self.update_ecommerce_prices(modified_prices)
        else:
            _logger.info("No prices are being modified.")

        # Ensure list_price and mercado_libre_price are the same if store_type is 'mercadolibre'
        if 'list_price' in vals or 'mercado_libre_price' in vals:
            for product in self:
                if product.store_type == 'mercadolibre':
                    if 'list_price' in vals:
                        vals['mercado_libre_price'] = vals['list_price']
                    elif 'mercado_libre_price' in vals:
                        vals['list_price'] = vals['mercado_libre_price']
       


        # 1. Detectar cambios en el precio
        if 'list_price' in vals:
            for product in self:
                old_price = product.list_price
                new_price = vals['list_price']
                if old_price != new_price:
                    # Crear un nuevo registro de evolución de precios
                    entry = self.env['vex.soluciones.price.evolution.data'].create({
                        'product_id': product.id,
                        'old_price': old_price,
                        'new_price': new_price,
                        'change_date': fields.Datetime.now(),
                    })
                    if entry:
                        _logger.info(f'Price change detected for product {product.id}: {old_price} -> {new_price}')
                    else:
                        _logger.info(f'Failed to create price evolution data for product {product.id}')
        
        # 2. Llamar al método `write` original
        res = super(InheritProductTemplate, self).write(vals)

        # 3. Detectar cambios en la imagen
        if 'image_1920' in vals:
            for product in self:
                if vals.get('image_1920'):
                    self.create_or_update_attachment(product, vals.get('image_1920'))


    

        return res

    def create_or_update_attachment(self, product, image_data):
        # Convertir los datos de la imagen a base64 (si no está ya en base64)
        if not isinstance(image_data, bytes):
            image_data = base64.b64decode(image_data)
        image_data_base64 = base64.b64encode(image_data).decode('utf-8')

        # Buscar si ya existe un attachment para el producto
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', product.id),
            ('name', '=', 'Product Image')
        ], limit=1)

        if attachment:
            # Actualizar el attachment existente
            attachment.write({
                'name': product.name,
                'datas': image_data_base64,
                'mimetype': 'image/jpeg',
            })
        else:
            # Crear un nuevo attachment y asignarlo al campo attachment_id
            attachment = self.env['ir.attachment'].create({
                'name': product.name,
                'type': 'binary',
                'datas': image_data_base64,
                'res_model': 'product.template',
                'res_id': product.id,
                'mimetype': 'image/jpeg',
                'public': True,
            })
            product.attachment_id = attachment
    
    @api.depends('sku_id')
    def _compute_group_ids(self):
        for product in self:
            if product.sku_id:
                product.group_ids = self.env['vex.group_product'].search([('sku_id', '=', product.sku_id.id)])
            else:
                product.group_ids = False

    @api.onchange('categ_id')
    def _onchange_categ_id(self):
        self.meli_category_code = self.categ_id.meli_code


    
    # LOGICA DE FORECAST
    @api.model
    def get_top_selling_products(self, limit=10):
        DashboardData = self.env['vex.dashboard.data']
        data_for = "top_selling_products"

        # Buscar registro existente
        record = DashboardData.search([('data_for', '=', data_for)], limit=1)
        if not record or record.last_updated < datetime.now() - timedelta(days=1):
            # Calcular la fecha de hace un mes
            date_from = datetime.now() - timedelta(days=30)
            date_from_str = date_from.strftime('%Y-%m-%d')

            # Buscar las líneas de pedido de venta en el último mes
            sale_order_lines = self.env['sale.order.line'].search([
                ('order_id.state', 'in', ['sale', 'done']),  # Solo contar ventas confirmadas
                ('order_id.date_order', '>=', date_from_str)
            ])

            # Crear un diccionario para contar las cantidades vendidas por producto
            product_sales = {}
            for line in sale_order_lines:
                if line.product_id.id in product_sales:
                    product_sales[line.product_id.id] += line.product_uom_qty
                else:
                    product_sales[line.product_id.id] = line.product_uom_qty

            # Ordenar los productos por cantidad vendida y limitar los resultados
            sorted_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)
            top_products = sorted_products[:limit]

            # Preparar los datos para guardar
            result = []
            for product_id, quantity in top_products:
                product = self.env['product.product'].browse(product_id)
                result.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'quantity_sold': quantity,
                    'stock_available': product.qty_available,
                })

            # Crear o actualizar el registro con los datos calculados
            record_data = {
                'month': 'N/A',  # No aplica para esta función
                'year': 0,  # No aplica
                'new_customers': 0,  # No aplica
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'extra_data': result  # Guardar los datos en un único campo JSON
            }
            if record:
                record.write(record_data)
            else:
                DashboardData.create(record_data)

            return result

        # Retornar los datos desde el campo extra_data
        return record.extra_data if 'extra_data' in record else []

    

    @api.model
    def get_product_info(self, product_id):
        # Buscar el producto por ID
        product = self.env['product.product'].browse(product_id)
        
        # Verificar si el producto existe
        if not product.exists():
            return {
                'error': 'Product not found'
            }
        
        # Preparar la información genérica del producto
        product_info = {
            'product_id': product.id,
            'product_name': product.name,
            'default_code': product.default_code,
            'list_price': product.list_price,
            'description': product.description,
            'stock_available': product.qty_available,
        }

         # Calcular la fecha de hace 70 días
        date_from = datetime.now() - timedelta(days=70)
        date_from_str = date_from.strftime('%Y-%m-%d')

         # Buscar las líneas de pedido de venta para el producto en los últimos 70 días
        sale_order_lines = self.env['sale.order.line'].search([
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', date_from_str),
            ('product_id', '=', product.id),
        ])
        
        # Crear un diccionario para contar las ventas diarias en los últimos 70 días
        daily_sales = {}
        for line in sale_order_lines:
            date_str = line.order_id.date_order.strftime('%Y-%m-%d')
            daily_sales[date_str] = daily_sales.get(date_str, 0) + line.product_uom_qty
        
        # Generar una lista de ventas diarias en los últimos 70 días
        sales_last_70_days = []
        for i in range(70):
            date_check = (date_from + timedelta(days=i)).strftime('%Y-%m-%d')
            sales_last_70_days.append(daily_sales.get(date_check, 0))
        
        # Añadir las ventas diarias al resultado final
        product_info['sales_last_70_days'] = sales_last_70_days
        
        product_info['forecast_data'] = self.action_prediccion(sales_last_70_days)
            
        return product_info
    
    def remove_trailing_zeros(self,sales_last_days):
    # Recorrer la lista en reversa y encontrar el primer número diferente de cero
        result = []
        for num in sales_last_days:
            if num != 0:
                result.append(num)
        return result
        
    def format_dates(self,date_range):
        # Formatear las fechas para que solo contengan el día
        return [date.strftime('%Y-%m-%d') for date in date_range]
    
    def action_export_product(self):
        _logger.info('Exporting product...')
        self.env['vex.soluciones.export.product']._compute_master_exists()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Exportar Producto',
            'res_model': 'vex.soluciones.export.product',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_name': self.name,
                'default_title': self.name,
                'default_image_1920_ml' : self.image_1920
            },
        }

    
    def action_prediccion(self, dataset):
        sales_last_days = dataset
        num_days = len(sales_last_days)

        end_date = pd.to_datetime('today').normalize()
        start_date = end_date - pd.DateOffset(days=num_days - 1)
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')

        # Crear el DataFrame en el formato que Prophet necesita
        data = pd.DataFrame({
            'ds': date_range,
            'y': [sales_last_days[i] if i < len(sales_last_days) else 0 for i in range(num_days)]
        })

        # Instanciar el modelo Prophet
        model = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=False)
        model.fit(data)

        # Crear el DataFrame para los próximos 7 días
        future = model.make_future_dataframe(periods=7)
        forecast = model.predict(future)

        # Extraer las predicciones para los próximos 7 días y asegurarse de que no haya valores negativos
        forecast_values = forecast[['ds', 'yhat']].tail(7)
        forecast_values['yhat'] = np.maximum(forecast_values['yhat'], 0)  # Ajustar a cero si es negativo

        # Preparar los datos para la salida
        formated_dates = self.format_dates(date_range.tolist())
        formated_forecast_dates = self.format_dates(forecast_values['ds'].tolist())
        stock_necessary = int(forecast_values['yhat'].sum())

        result = {
            'dates': formated_dates,
            'sales': [sale for sale in dataset],  # Usar la lista original para ventas
            'forecast_dates': formated_forecast_dates,
            'forecast_sales': forecast_values['yhat'].tolist(),
            'stock_necessary': stock_necessary,
        }

        return result



    @api.model
    def calculate_table_data(self ,products_dict):    
        for product in products_dict:
            product_info = self.get_product_info(product['product_id'])
            
            product['stock_necessary'] = product_info['forecast_data']['stock_necessary']
            product['current_stock'] = product_info['stock_available']
            product['default_code'] = product_info['default_code']

        
        return products_dict
    

    # Dashboard functions


    #Mercado libre API-CALLS
    def update_product_price_mercadolibre(self,item_id: str, new_price: float, access_token: str):
        """
        Modifica el precio de un producto publicado en Mercado Libre.

        :param item_id: ID de la publicación en Mercado Libre.
        :param new_price: Nuevo precio que se desea establecer.
        :param access_token: Token de acceso a la API de Mercado Libre.
        :return: Respuesta de la API en formato JSON o None en caso de error.
        """

        response = None  # Inicializar response para evitar errores de referencia
        
        # Construir la URL de la solicitud
        url = f"{MERCADO_LIBRE_URL}/items/{item_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Datos que vamos a actualizar
        payload = {
            "price": round(float(new_price), 2)
        }
        
        try:
            # Log de la solicitud
            _logger.info(f"URL de la solicitud: {url}")
            _logger.info(f"Headers de la solicitud: {headers}")
            _logger.info(f"Payload enviado: {payload}")

            # Hacer la solicitud PUT a Mercado Libre
            response = requests.put(url, headers=headers, json=payload)
            
            response.raise_for_status()  # Lanza una excepción si el código de estado no es 200

            # Log de la respuesta exitosa
            _logger.info(f"Precio actualizado exitosamente en Mercado Libre.")
            _logger.info(f"Respuesta de la API: {response.json()}")

            return response.json()

        except requests.RequestException as e:
            _logger.error(f"Error al actualizar el precio en Mercado Libre: {str(e)}")
            
            error_message = "Error desconocido"
            if response is not None:
                _logger.error(f"Respuesta de la API: {response.status_code}")
                _logger.error(f"Contenido de la respuesta: {response.text}")

                try:
                    error_message = response.json().get("message", response.text)
                except ValueError:
                    error_message = response.text  # Si no es JSON válido, usa el texto de respuesta

            raise UserError(f"Error al actualizar el precio en Mercado Libre: {error_message}")
        

    #Walmart API-Calls
    def update_product_price_walmart(sku: str, new_price: float, access_token: str):
        """
        Modifica el precio de un producto publicado en Walmart.

        :param sku: SKU del producto en Walmart.
        :param new_price: Nuevo precio que se desea establecer.
        :param access_token: Token de acceso a la API de Walmart.
        :return: Respuesta de la API en formato JSON o None en caso de error.
        """

        response = None  # Inicializar response para evitar errores de referencia

        # Construir la URL de la solicitud
        url = WALMART_API_URL
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Datos que vamos a actualizar
        payload = {
            "sku": sku,
            "pricing": [
                {
                    "currentPriceType": "BASE",
                    "currentPrice": {
                        "currency": "MXN",  # Asegúrate de usar la moneda correcta
                        "amount": round(float(new_price), 2)
                    }
                }
            ]
        }

        try:
            # Log de la solicitud
            _logger.info(f"URL de la solicitud: {url}")
            _logger.info(f"Headers de la solicitud: {headers}")
            _logger.info(f"Payload enviado: {payload}")

            # Hacer la solicitud PUT a Walmart
            response = requests.put(url, headers=headers, json=payload)

            response.raise_for_status()  # Lanza una excepción si el código de estado no es 200

            # Log de la respuesta exitosa
            _logger.info(f"Precio actualizado exitosamente en Walmart.")
            _logger.info(f"Respuesta de la API: {response.json()}")

            return response.json()

        except requests.RequestException as e:
            _logger.error(f"Error al actualizar el precio en Walmart: {str(e)}")

            error_message = "Error desconocido"
            if response is not None:
                _logger.error(f"Respuesta de la API: {response.status_code}")
                _logger.error(f"Contenido de la respuesta: {response.text}")

                try:
                    error_message = response.json().get("message", response.text)
                except ValueError:
                    error_message = response.text  # Si no es JSON válido, usa el texto de respuesta

            raise Exception(f"Error al actualizar el precio en Walmart: {error_message}")

    #Shopify API-Calls
    def actualizar_precio_shopify(api_key, password, tienda, id_producto, id_variante, nuevo_precio):
        url = f"https://{api_key}:{password}@{tienda}.myshopify.com/admin/api/2024-10/products/{id_producto}.json"
        headers = {
            "Content-Type": "application/json",
        }
        payload = {
            "product": {
                "id": id_producto,
                "variants": [
                    {
                        "id": id_variante,
                        "price": nuevo_precio
                    }
                ]
            }
        }
        response = requests.put(url, json=payload, headers=headers)
        if response.status_code == 200:
            print("Precio actualizado correctamente en Shopify.")
        else:
            print(f"Error al actualizar el precio en Shopify: {response.status_code} - {response.text}")

    #Amazon API-Calls

    def actualizar_precio_amazon(aws_access_key, aws_secret_key, region, marketplace_id, seller_id, sku, nuevo_precio):
        from requests.auth import AWS4Auth
        endpoint = f"https://sellingpartnerapi-na.amazon.com/listings/2021-08-01/items/{seller_id}/{sku}/prices"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "marketplaceId": marketplace_id,
            "price": {
                "listingPrice": {
                    "value": str(nuevo_precio),
                    "currencyCode": "MXN"
                }
            }
        }
        awsauth = AWS4Auth(aws_access_key, aws_secret_key, region, 'execute-api')
        response = requests.put(endpoint, auth=awsauth, json=payload, headers=headers)
        if response.status_code == 200:
            print("Precio actualizado correctamente en Amazon.")
        else:
            print(f"Error al actualizar el precio en Amazon: {response.status_code} - {response.text}")

    def show_success_notification(self,message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Éxito',
                'message': message,
                'type': 'success',  # Tipos: success, warning, danger, info
                'sticky': False,    # True para mantener el mensaje visible hasta que el usuario lo cierre
            },
        }

    @api.model
    def generar_precio_automatico(self):   
        return UserError("Error")
    
class InheritProductTemplateUnits(models.Model):
    _name = 'product.template.units'

    def get_permalink(self):
        self.permalink = self.product_id.permalink

    product_id = fields.Many2one('product.template', string='Product')
    meli_code = fields.Char('Publication ID')
    quantity = fields.Integer('Quantity')
    permalink = fields.Char('Permalink', compute=get_permalink)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')