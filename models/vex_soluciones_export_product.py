from odoo import models, fields
import logging
import requests
from odoo.exceptions import UserError
import base64

_logger = logging.getLogger(__name__)

MERCADO_LIBRE_API_URL = "https://api.mercadolibre.com"

class VexSolutionsExportProduct(models.Model):
    _name = 'vex.soluciones.export.product'
    _description = 'Exportar Producto'

    product_name = fields.Char(string='Producto')
    title = fields.Char(string='Título')
    category_predicted = fields.Boolean(string='Categoría Predicha', default=False)

    #Multichanel configuration
    instance = fields.Many2one('vex.instance', string='Instance') 
    instance_mercado_libre = fields.Many2one('vex.instance', string='Instance Mercado Libre')
    instance_amazon = fields.Many2one('vex.instance', string='Instance Amazon')
    instance_shopify = fields.Many2one('vex.instance', string='Instance Shopify')
    instance_walmart = fields.Many2one('vex.instance', string='Instance Walmart')

    #Bool variables to indicate wich store export the product
    export_to_mercado_libre = fields.Boolean(string='Exportar a Mercado Libre')
    export_to_amazon = fields.Boolean(string='Exportar a Amazon')
    export_to_shopify = fields.Boolean(string='Exportar a Shopify')
    export_to_walmart = fields.Boolean(string='Exportar a Walmart')

    #WALMART FIELDS
    # Campos requeridos por Walmart
    walmart_sku = fields.Char(string="Walmart SKU", help="SKU único del producto en Walmart")
    walmart_product_id = fields.Char(string="Walmart Product ID", help="UPC, EAN o GTIN del producto")
    walmart_product_id_type = fields.Selection([
        ('UPC', 'UPC'),
        ('GTIN', 'GTIN'),
        ('EAN', 'EAN')
    ], string="Tipo de Product ID")
    walmart_short_description = fields.Text(string="Descripción Corta", help="Breve descripción del producto")
    walmart_brand = fields.Char(string="Marca", help="Marca del producto")
    walmart_main_image_url = fields.Char(string="URL de Imagen Principal", help="URL de la imagen principal del producto")
    walmart_product_category = fields.Char(string="Categoría de Producto", help="Categoría del producto en Walmart")
    walmart_price = fields.Float(string="Precio", help="Precio del producto")
    walmart_price_currency = fields.Selection([
        ('USD', 'USD'),
        ('EUR', 'EUR'),
    ], string="Moneda del Precio", default='USD')
    walmart_shipping_weight = fields.Float(string="Peso para Envío", help="Peso del producto para envío")
    walmart_shipping_weight_unit = fields.Selection([
        ('lb', 'Libras'),
        ('kg', 'Kilogramos')
    ], string="Unidad de Peso", default='lb')

    # Campos opcionales
    walmart_long_description = fields.Text(string="Descripción Larga", help="Descripción detallada del producto")
    walmart_additional_images = fields.Text(string="URLs de Imágenes Adicionales", help="Lista separada por comas de URLs de imágenes adicionales")
    walmart_msrp = fields.Float(string="MSRP", help="Precio sugerido por el fabricante")
    walmart_fulfillment_lag_time = fields.Integer(string="Tiempo de Cumplimiento (días)", help="Días para procesar el pedido antes del envío")
    walmart_variants = fields.Text(string="Variantes", help="Detalles de variantes del producto, como tamaño o color")
    walmart_tax_code = fields.Char(string="Código Fiscal", help="Código fiscal del producto")
    walmart_ingredients = fields.Text(string="Ingredientes", help="Lista de ingredientes del producto")
    walmart_legal_disclaimer = fields.Text(string="Aviso Legal", help="Información legal del producto")
    walmart_country_of_origin = fields.Char(string="País de Origen", help="País de origen del producto")
    walmart_safety_warnings = fields.Text(string="Advertencias de Seguridad", help="Advertencias relacionadas con el producto")
    walmart_key_features = fields.Text(string="Características Clave", help="Lista separada por comas de las características principales del producto")
    walmart_warranty = fields.Text(string="Garantía", help="Información sobre la garantía del producto")

    #AMAZON FIELDS
    # Campos requeridos
    amazon_seller_sku = fields.Char(string="Seller SKU", help="Identificador único del producto para el vendedor")
    amazon_product_type = fields.Char(string="Tipo de Producto", help="El tipo de producto (por ejemplo, ELECTRONICS, APPAREL)")
    amazon_item_name = fields.Char(string="Nombre del Producto", help="Nombre del producto que aparecerá en Amazon")
    amazon_brand = fields.Char(string="Marca", help="Marca del producto")
    amazon_manufacturer = fields.Char(string="Fabricante", help="Fabricante del producto")
    amazon_description = fields.Text(string="Descripción", help="Descripción completa del producto")
    amazon_bullet_points = fields.Text(string="Puntos Clave", help="Lista de características principales separadas por comas")
    amazon_standard_product_id_type = fields.Selection([
        ('UPC', 'UPC'),
        ('EAN', 'EAN'),
        ('GTIN', 'GTIN')
    ], string="Tipo de Identificador del Producto")
    amazon_standard_product_id_value = fields.Char(string="Valor del Identificador del Producto", help="UPC, EAN o GTIN del producto")
    amazon_fulfillment_channel = fields.Selection([
        ('DEFAULT', 'DEFAULT'),
        ('FBA', 'Fulfilled by Amazon')
    ], string="Canal de Cumplimiento", default='DEFAULT')
    amazon_fulfillment_quantity = fields.Integer(string="Cantidad Disponible", help="Cantidad disponible para el canal seleccionado")
    amazon_condition_type = fields.Selection([
        ('New', 'New'),
        ('UsedLikeNew', 'Used Like New'),
        ('UsedGood', 'Used Good')
    ], string="Condición del Producto", default='New')
    amazon_cost = fields.Float(string="Costo", help="Costo del producto")

    # Campos opcionales
    amazon_variation_theme = fields.Char(string="Tema de Variación", help="Tema de variación (tamaño, color, etc.)")
    amazon_dimensions_length = fields.Float(string="Longitud", help="Longitud del producto")
    amazon_dimensions_width = fields.Float(string="Ancho", help="Ancho del producto")
    amazon_dimensions_height = fields.Float(string="Altura", help="Altura del producto")
    amazon_weight = fields.Float(string="Peso", help="Peso del producto")
    amazon_msrp = fields.Float(string="Precio Sugerido", help="Precio sugerido por el fabricante")
    amazon_images = fields.Text(string="URLs de Imágenes", help="Lista separada por comas de URLs de imágenes adicionales")
    amazon_max_order_quantity = fields.Integer(string="Cantidad Máxima por Pedido", help="Cantidad máxima que un cliente puede pedir")
    amazon_shipping_template_id = fields.Char(string="ID de Plantilla de Envío", help="ID de la plantilla de envío asignada")


    # Image field
    image_1920_ml = fields.Binary(string='Image', attachment=True, help="Image of the product")

    #SHOPIFY FIELDS
    # Campos requeridos
    shopify_title = fields.Char(string="Título", help="Nombre del producto en Shopify")
    shopify_body_html = fields.Text(string="Descripción HTML", help="Descripción completa del producto en formato HTML")
    shopify_vendor = fields.Char(string="Proveedor", help="Proveedor del producto")
    shopify_product_type = fields.Char(string="Tipo de Producto", help="Categoría o tipo de producto")
    shopify_price = fields.Float(string="Precio", help="Precio del producto")
    shopify_status = fields.Selection([
        ('active', 'Activo'),
        ('draft', 'Borrador'),
        ('archived', 'Archivado')
    ], string="Estado del Producto", default='draft')

    # Variantes (al menos una es obligatoria)
    shopify_sku = fields.Char(string="SKU", help="SKU único del producto")
    shopify_inventory_quantity = fields.Integer(string="Cantidad en Inventario", help="Cantidad de inventario disponible")

    # Campos opcionales
    shopify_tags = fields.Char(string="Etiquetas", help="Etiquetas separadas por comas")
    shopify_images = fields.Text(string="URLs de Imágenes", help="Lista separada por comas de URLs de imágenes")
    shopify_options = fields.Text(string="Opciones", help="Opciones de variantes como tamaño o color")
    shopify_handle = fields.Char(string="Handle", help="Identificador único en la URL de Shopify")
    shopify_metafields = fields.Text(string="Metafields", help="Metadatos personalizados del producto")
    shopify_inventory_management = fields.Selection([
        ('shopify', 'Shopify'),
        ('external', 'Externo')
    ], string="Gestión de Inventario", default='shopify')
    shopify_compare_at_price = fields.Float(string="Precio de Comparación", help="Precio original para mostrar descuentos")
    shopify_weight = fields.Float(string="Peso", help="Peso del producto")
    shopify_weight_unit = fields.Selection([
        ('kg', 'Kilogramos'),
        ('lb', 'Libras')
    ], string="Unidad de Peso", default='kg')
    shopify_collections = fields.Text(string="Colecciones", help="Lista de colecciones a las que pertenece el producto")

    #MERCADO LIBRE FIELDS
    mercado_libre_price = fields.Float(string="Mercado Libre Price")
    ml_category_id = fields.Char(string='Category ID', help="ID of the category in Mercado Libre")
    ml_category_name = fields.Char(string='Category Name', help="Final name of the category in Mercado Libre")

    ml_picture = fields.Char(string='Imagen de Mercado Libre', help="URL de la imagen del producto en Mercado Libre")

    category = fields.Selection([
        ('electronics', 'Electrónica'),
        ('fashion', 'Moda'),
        ('home_appliances', 'Electrodomésticos'),
        ('toys', 'Juguetes'),
        ('sports', 'Deportes'),
        ('beauty', 'Belleza y Cuidado Personal'),
        ('health', 'Salud'),
        ('automotive', 'Automotriz'),
        ('books', 'Libros'),
        ('music', 'Música'),
        ('art', 'Arte y Coleccionables'),
        ('real_estate', 'Bienes Raíces'),
        ('jobs', 'Empleos'),
        # Más categorías basadas en Mercado Libre
    ], string='Categoría')
    sub_category = fields.Selection([
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('consoles', 'Consolas'),
        ('computers', 'Computadoras'),
        ('phones', 'Celulares y Teléfonos'),
        ('clothing', 'Ropa'),
        ('footwear', 'Calzado'),
        ('kitchen_appliances', 'Electrodomésticos de Cocina'),
        ('personal_care', 'Cuidado Personal'),
        ('sports_equipment', 'Equipo Deportivo'),
        ('cycling', 'Ciclismo'),
        ('makeup', 'Maquillaje'),
        ('skin_care', 'Cuidado de la Piel'),
        ('books_fiction', 'Libros de Ficción'),
        ('books_nonfiction', 'Libros de No Ficción'),
        ('vehicles_parts', 'Partes de Vehículos'),
        ('music_instruments', 'Instrumentos Musicales'),
        ('collectibles', 'Coleccionables'),
        # Más subcategorías específicas
    ], string='Sub Categoría')
    sub_sub_category = fields.Selection([
        ('smartphones', 'Smartphones'),
        ('headphones', 'Auriculares'),
        ('refrigerators', 'Refrigeradores'),
        ('microwaves', 'Microondas'),
        ('gaming', 'Videojuegos'),
        ('fiction_novels', 'Novelas de Ficción'),
        ('nonfiction_biographies', 'Biografías'),
        ('bicycles', 'Bicicletas'),
        ('sports_clothing', 'Ropa Deportiva'),
        ('skin_treatment', 'Tratamiento de Piel'),
        ('perfumes', 'Perfumes'),
        ('guitars', 'Guitarras'),
        ('vinyl_records', 'Discos de Vinilo'),
        # Más sub-subcategorías detalladas
    ], string='Sub Sub Categoría')
    product_condition = fields.Selection([
        ('new', 'Nuevo'),
        ('used', 'Usado'),
        ('refurbished', 'Reacondicionado'),
        # Más condiciones si son necesarias
    ], string='Condición del Producto', default='new')
    stock = fields.Integer(string='Stock', default=0)
    purchase_mode = fields.Selection([
        ('buy_now', 'Compre ya'),
        ('auction', 'Subasta'),
    ], string='Modo de Compra', default='buy_now')
    publication_type = fields.Selection([
        ('gold_special', 'Gold Special'),
        ('gold_pro', 'Gold Pro'),
        ('free', 'Free'),
    ], string='Tipo de Publicación', default='gold_special')
    description = fields.Text(string='Descripción')


   

    master_exists = fields.Boolean(string="¿Master existe?", compute="_compute_master_exists", store=False)

    
        
    def _compute_master_exists(self):
        """Verifica si hay algún usuario con master=True."""
        master_user = self.env['res.users'].search([('is_question_responder', '=', True)], limit=1)
        for record in self:
            record.master_exists = bool(master_user)
            _logger.info('master_exists: %s', record.master_exists)

    def action_export(self):
        _logger.info("Exportando producto a las tiendas")              
        
        if self.export_to_mercado_libre:
            _logger.info("Corriendo logica de exportacion hacia Mercado Libre")
            #Llamada al api
            self.export_to_ml()

    def export_to_ml(self):
        _logger.info("Primero obtenemos la categoria del producto")

        

        cateory_id, category_name = self.predict_category_ml()

        if not cateory_id or not category_name:
            raise ValueError("No se pudo predecir la categoría del producto en Mercado Libre.")
        

        
        self.create_product_in_mercado_libre(access_token=self.instance_mercado_libre.access_token)
        





    def predict_category_ml(self):
        get_category = self.predict_category_in_mercado_libre(product_title=self.title,limit=1)

        _logger.info(f"La respuesta es {get_category} ")

        category_id = get_category[0]['category_id']
        category_name = get_category[0]['category_name']

        _logger.info(f"Categoría ID: {category_id}")
        _logger.info(f"Categoría Nombre: {category_name}")

        self.ml_category_id = category_id
        self.ml_category_name = category_name

        return category_id, category_name
        

    #Modelos de exportacion para mercado libre

    def save_and_upload_image_to_ml(self):
        if not self.image_1920_ml:
            raise UserError("No se ha proporcionado una imagen para el producto.")
        
        image_binary = base64.b64decode(self.image_1920_ml)
        # Aquí puedes agregar la lógica para guardar y subir la imagen a Mercado Libre

        _logger.info("Guardando imagen del producto en el archivo 'producto_odoo.jpg'.")

        with open("producto_odoo.jpg", "wb") as f:
            f.write(image_binary)

        ml_url = "https://api.mercadolibre.com/pictures/items/upload"
        ml_headers = {
            "Authorization": f"Bearer {self.instance_mercado_libre.access_token}"
        }

        import os

        if os.path.exists("producto_odoo.jpg"):
            _logger.info("Imagen guardada correctamente en el archivo 'producto_odoo.jpg'.")
        else:
            _logger.info("No se encontró la imagen después de guardarla.")

        # Subir la imagen
        files = {"file": open("producto_odoo.jpg", "rb")}

        if not files:
            _logger.info("Nope")


        
        try:
            response = requests.post(ml_url, headers=ml_headers, files=files)
            response.raise_for_status()  # Eleva una excepción si el código de estado no es 200

            # Obtener la respuesta
            picture_data = response.json()
            _logger.info(f"Respuesta de la API de Mercado Libre: {response.json()}")
            picture_id = picture_data.get("id")
            _logger.info(f"Imagen subida con éxito a Mercado Libre. ID: {picture_id}")
        except requests.RequestException as e:
            _logger.error(f"Error al subir la imagen a Mercado Libre: {str(e)}")
            if response:
                _logger.error(f"Respuesta de la API: {response.status_code}")
                _logger.error(f"Contenido de la respuesta: {response.text}")
            raise UserError("Error al subir la imagen a Mercado Libre.")

    def create_product_in_mercado_libre(
        self, 
        #title: str,
        #category_id: str,
        #price: float,
        #currency_id: str, #Tenemos que pasar estamanualmente
        #available_quantity: int,
        #buying_mode: str,
        #condition: str,
       # listing_type_id: str,
        #description: str,
        #pictures: list, #Aqui sera el unico "problema"
        access_token: str
    ):
        """
        Crea un producto en Mercado Libre usando su API.

        :param title: Título del producto.
        :param category_id: ID de la categoría en Mercado Libre.
        :param price: Precio del producto.
        :param currency_id: Moneda del producto (ejemplo: ARS para pesos argentinos).
        :param available_quantity: Cantidad disponible del producto.
        :param buying_mode: Modo de compra (ejemplo: "buy_it_now" para compra inmediata).
        :param condition: Condición del producto (ejemplo: "new" o "used").
        :param listing_type_id: Tipo de publicación en Mercado Libre.
        :param description: Descripción del producto.
        :param pictures: Lista de URLs de imágenes del producto (formato: [{"source": "url"}]).
        :param access_token: Token de acceso a la API de Mercado Libre.
        :return: Respuesta de la API de Mercado Libre en formato JSON.
        """
        _logger.info("Iniciando creación de producto en Mercado Libre.")
        self.save_and_upload_image_to_ml()


        # Crear el diccionario con los datos del producto
        required_fields = {
            "title": self.title,
            "category_id": self.ml_category_id,
            "price": self.mercado_libre_price,
            "currency_id": "MXN",
            "available_quantity": self.stock,
            "buying_mode": self.purchase_mode,
            "condition": self.product_condition,
            "listing_type_id": self.publication_type,
            "description": self.description,
            "pictures": [
            {
                "id": "123-MLA456_112021"
            }
   ]
        }

        # Log de los valores de las variables
        for field, value in required_fields.items():
            _logger.info(f"{field}: {value}")

        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            error_message = f"Faltan los siguientes campos requeridos: {', '.join(missing_fields)}"
            _logger.error(error_message)
            raise UserError(error_message)

        
        return
        product_data = required_fields

        # URL para la creación de productos
        url = f"{MERCADO_LIBRE_API_URL}/items"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            # Log de los datos enviados
            _logger.info(f"Datos del producto: {product_data}")
            _logger.info(f"URL de la solicitud: {url}")
            _logger.info(f"Headers de la solicitud: {headers}")

            # Realizar la solicitud POST
            response = requests.post(url, headers=headers, json=product_data)
            response.raise_for_status()  # Eleva una excepción si el código de estado no es 200

            # Log de la respuesta exitosa
            _logger.info(f"Producto creado exitosamente. Código de estado: {response.status_code}")
            _logger.info(f"Contenido de la respuesta: {response.text}")

            # Retornar los datos del producto creado
            return response.json()

        except requests.RequestException as e:
            _logger.error(f"Error al crear el producto en Mercado Libre: {str(e)}")
            if response:
                _logger.error(f"Respuesta de la API: {response.status_code}")
                _logger.error(f"Contenido de la respuesta: {response.text}")
            return None
        
    def predict_category_in_mercado_libre(self, product_title: str, limit: int = 1):
        """
        Predice la categoría de un producto en Mercado Libre usando su API.

        :param product_title: Título del producto para el cual se desea predecir la categoría.
        :param site_id: ID del sitio de Mercado Libre (ejemplo: MLA para Argentina, MLM para México).
        :param access_token: Token de acceso a la API de Mercado Libre.
        :param limit: Número de categorías a retornar (por defecto es 1, máximo es 8).
        :return: Lista de categorías sugeridas con sus detalles.
        """
        _logger.info("Iniciando predicción de categoría en Mercado Libre.")

        current_user = self.env.user 
        instance = current_user.meli_instance_id

        SITE_ID = instance.meli_country

        #instance = self.env['vex.instance'].search([('store_type', '=', 'mercadolibre')], limit=1)
        #instance = self.env['vex.instance'].search([('id', '=', 5)], limit=1)
            

        # URL para la predicción de categorías
        url = f"{MERCADO_LIBRE_API_URL}/sites/{SITE_ID}/domain_discovery/search"
         # ID del sitio de Mercado Libre (ejemplo: MLA para Argentina, MLM para México)
        headers = {
            "Authorization": f"Bearer {instance.access_token}",
            "Content-Type": "application/json",
        }
        params = {
            "q": product_title,
            "limit": limit
        }

        try:
            # Log de los datos enviados
            _logger.info(f"Título del producto: {product_title}")
            _logger.info(f"URL de la solicitud: {url}")
            _logger.info(f"Headers de la solicitud: {headers}")
            _logger.info(f"Parámetros de la solicitud: {params}")

            # Realizar la solicitud GET
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Eleva una excepción si el código de estado no es 200

            # Log de la respuesta exitosa
            _logger.info(f"Predicción de categoría exitosa. Código de estado: {response.status_code}")
            _logger.info(f"Contenido de la respuesta: {response.text}")

            # Retornar las categorías sugeridas
            return response.json()

        except requests.RequestException as e:
            _logger.error(f"Error al predecir la categoría en Mercado Libre: {str(e)}")
            if response:
                _logger.error(f"Respuesta de la API: {response.status_code}")
                _logger.error(f"Contenido de la respuesta: {response.text}")
            return None