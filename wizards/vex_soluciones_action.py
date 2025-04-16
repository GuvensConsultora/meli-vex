import uuid
from odoo import models,fields,api
import requests
import json
from odoo.exceptions import ValidationError, UserError
import logging
import base64
from datetime import datetime,timedelta
import time
import urllib.parse
from typing import List
from io import BytesIO  # Asegúrate de que esto esté importado
import random
import xlsxwriter
import pytz
import re


_logger = logging.getLogger(__name__)

GET_ORDER="https://api.mercadolibre.com/orders/search?seller={}&order.date_created.from={}&order.date_created.to={}&sort=date_desc&limit={}&offset={}"
ME_URI="https://api.mercadolibre.com/users/me"
MERCADO_LIBRE_URL = 'https://api.mercadolibre.com'

RUT_URI="https://api.mercadolibre.com/orders/{}/billing_info"

class VexSolucionesAction(models.TransientModel):
    _name = "vex.import.wizard"
    _description = "Wizard Model to trigger import/update actions"

    vex_instance_id = fields.Many2one('vex.instance', string='Instance')

    vex_actions = fields.Selection([
        ('product', 'Product'),
        ('category', 'Category'),
        ('customer', 'Customer'),
        ('order', 'Order'),
        ('pricelist', 'Pricelist'),
        ('questions', 'Questions'),
        ('excel_data', 'ExcelData') ,       
        ('pruebas', 'Pruebas') 
    ], string='Action', required=True)
    import_unit = fields.Boolean('Import Unit')
    meli_code_unit = fields.Char('Meli Code')

    # product
    stock_import = fields.Boolean('Stock import')
    import_images = fields.Boolean('Import images')
    import_images_website = fields.Selection([
        ('save_url', 'Save url'),
        ('save_url_and_download', 'Save url and download')
    ], string='Import images website')

    import_excel_data = fields.Selection([
        ('product_cost', 'Product Cost ML/$'),
        ('other', 'Other...')
    ], string='Type of sync: ')


    # customer
    date_from = fields.Datetime('Date from')
    date_to = fields.Datetime('Date to')
    
    def extract_domain(self, url):
        parsed_url = urllib.parse.urlparse(url)
        return parsed_url.netloc

    def validate_licence(self):
        return True
        if not (self.vex_instance_id.license_secret_key and self.vex_instance_id.license_key and self.vex_instance_id.url_license and self.vex_instance_id.registered_domain):
            raise ValidationError('You should add a Secret key and licence key to continue')
        
        url = '{}?slm_action=slm_check&secret_key={}&license_key={}&registered_domain={}'.format(self.vex_instance_id.url_license, self.vex_instance_id.license_secret_key, self.vex_instance_id.license_key, self.extract_domain(self.vex_instance_id.registered_domain))

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        try:
            r = requests.get(url=url, headers=headers)
            r.raise_for_status()  # Raise an error for non-200 status codes
            response_json = r.json()  # Try to parse JSON
        except requests.exceptions.RequestException as e:
            print(e)
            raise ValidationError('Error in consumption')
        except json.JSONDecodeError as e:
            print(e)
            raise ValidationError('Error in consumption')
        
        print(r)
        
        # Check for expected key and handle validation result
        if 'result' not in response_json:
            raise ValidationError("Unexpected response format from license server.")

        if response_json['result'] != 'success':
            # Provide specific error messages based on potential issues
            if 'message' in response_json:
                error_message = response_json['message']
            else:
                error_message = "License validation failed. Please contact support."

            raise ValidationError(error_message)
        

    @api.model
    def default_get(self, fields):
        res = super(VexSolucionesAction, self).default_get(fields)

        # Acceder al contexto completo
        context = self.env.context

        # Registrar en los logs todos los valores del contexto
        _logger = logging.getLogger(__name__)
        if context:
            for_stores = context.get('for_stores', None)  # None si no existe
            _logger.info("Contexto completo recibido:")
            for key, value in context.items():
                _logger.info(f"Clave: {key}, Valor: {value}")
        else:
            _logger.info("No se recibió contexto.")

        return res

    def synchronize(self):
        self.validate_licence()
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Bearer {self.vex_instance_id.access_token}'}

        store_type = self.env.context.get('store_type')
        
        if store_type:
            _logger.info(f"Consulta para la tienda: {store_type}")

        if store_type == 'mercadolibre':   
            if self.vex_actions == 'category':
                if not self.import_unit:
                    self.synchronize_category(headers)
                else:
                    self.synchronize_unit_category(headers, self.meli_code_unit, self.vex_instance_id.id)
            elif self.vex_actions == 'product':
                if not self.import_unit:
                    self.get_product_sku(self.vex_instance_id.user_id, headers)
                else:
                    self.get_product_item(self.meli_code_unit, headers)
            elif self.vex_actions == 'customer':
                self.get_customer(headers)
            elif self.vex_actions == 'order':
                if not self.import_unit:
                    self.get_order(headers)
            elif self.vex_actions == 'pricelist':
                if not self.import_unit:
                    self.get_pricelist(headers)
            elif self.vex_actions == 'questions':
                if not self.import_unit:
                    self.get_questions(headers)     
            elif self.vex_actions == 'excel_data':
                if not self.import_unit:
                    self.import_excel(headers)   
            elif self.vex_actions == 'pruebas':            
                self.pruebas() 

        return self.vex_instance_id

    def mensajeria_interna(self):
        """
        Método de prueba para enviar un mensaje a una orden utilizando un usuario predeterminado.
        """
        # Parámetros de prueba
        meli_code = "2000010067658104"  # Reemplaza con un código válido de prueba
        author_name = "Seller part"  # Autor predeterminado
        message_body = "Este es un mensaje de prueba enviado por Seller part. En teoria 30 minutos ago"

        # Buscar la orden por meli:code
        order = self.env['sale.order'].search([('meli_code', '=', meli_code)], limit=1)
        if not order:
            raise ValueError(f"No se encontró ninguna orden con el código Mercado Libre: {meli_code}")

        # Crear un mensaje en la orden
        message = self.env['vex.mediations'].create_message_for_order(meli_code ,author_name, message_body)

        return message

    def pruebas(self):
        _logger.info("Iniciando pruebas")
        url_ ="https://articulo.mercadolibre.com.mx/MLM-2876206672-botas-mujer-trabajo-casquillo-negras-cafes-ram-401-d-_JM#reco_item_pos=2&reco_backend=item_decorator&reco_backend_type=function&reco_client=home_items-decorator-legacy&reco_id=88427083-22fa-49e4-bd69-3707e59eae68&reco_model=&c_id=/home/bookmarks-recommendations-seed/element&c_uid=54c7b295-40da-4aa6-9cd0-9169d6e051d8&da_id=bookmark&da_position=2&id_origin=/home/dynamic_access&da_sort_algorithm=ranker"
        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id
        
        access = meli_instance.access_token
        #access = instance = self.env['vex.instance'].search([('store_type', '=', 'mercadolibre')], limit=1) # Idea original
        #access = self.env['vex.instance'].search([('id', '=', 5)], limit=1).access_token
        _logger.info(self.get_product_info(product_url=url_,access_token=access))

    def get_product_info(self, product_url: str, access_token):
        """
        Obtiene la información de un producto en Mercado Libre dado un link.

        :param product_url: URL del producto en Mercado Libre.
        :return: JSON con la información del producto o None en caso de error.
        """
        _logger.info("Iniciando obtención de información del producto.")

        # Extraer el ID del producto
        meli_id = self.extract_meli_id(product_url)
        
        if not meli_id:
            _logger.error("No se pudo extraer el ID del producto de la URL.")
            return None
        
        url = f"{MERCADO_LIBRE_URL}/items/{meli_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            _logger.info(f"Solicitando información del producto con ID: {meli_id}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            _logger.info("Información del producto obtenida correctamente.")
            return response.json()
        
        except requests.RequestException as e:
            _logger.error(f"Error al obtener la información del producto: {str(e)}")
            return None
        
    def extract_meli_id(self, url: str) -> str:
        """
        Extrae el ID de un producto de una URL de Mercado Libre.

        :param url: URL del producto en Mercado Libre.
        :return: ID del producto (MELI ID) o None si no se puede extraer.
        """
        match = re.search(r'/ML[ABM]-\d+', url)
        if match:
            valor = match.group().strip("/")
            valor = valor.replace("-", "")
            return  valor # Devuelve el ID sin los slashes
        return None
        
    def get_messages(self, order_id: str, access_token: str, seller_id: str, debug: bool = False):
        """
        Obtiene todos los mensajes asociados a un order_id desde el endpoint de mensajería de Mercado Libre.
        
        :param order_id: ID de la orden en Mercado Libre.
        :param access_token: Token de acceso de Mercado Libre.
        :param seller_id: ID del vendedor.
        :param debug: Si está en True, habilita logs detallados para debug.
        :return: Lista completa de mensajes o None si ocurre un error.
        """
        if debug:
            _logger.info(f"Iniciando la obtención de mensajes para el order_id: {order_id}")
        
        url = f"{MERCADO_LIBRE_URL}/messages/packs/{order_id}/sellers/{seller_id}?tag=post_sale&limit=50"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        all_messages = []
        offset = 0

        try:
            while True:
                paginated_url = f"{url}&offset={offset}"
                if debug:
                    _logger.info(f"URL de la solicitud paginada: {paginated_url}")
                    _logger.info(f"Headers de la solicitud: {headers}")
                
                response = requests.get(paginated_url, headers=headers)
                response.raise_for_status()

                data = response.json()
                messages = data.get('messages', [])
                
                if debug:
                    _logger.info(f"Mensajes obtenidos exitosamente para offset {offset}")
                    _logger.info(f"Respuesta de la API: {response.status_code}")
                    _logger.info(f"Contenido de la respuesta: {response.text}")
                
                all_messages.extend(messages)
                
                # Verificar si hay más mensajes que obtener
                paging = data.get('paging', {})
                total = paging.get('total', 0)
                limit = paging.get('limit', 50)
                offset += limit
                
                if offset >= total:
                    break
            
            if debug:
                _logger.info(f"Total de mensajes obtenidos: {len(all_messages)}")
            
            return all_messages
        
        except requests.exceptions.RequestException as e:
            if debug:
                _logger.error(f"Error al obtener los mensajes: {e}")
            return None
    
    def procesar_mensajes(self,mensajes):
        """
        Procesa una lista de mensajes para extraer información relevante y evitar duplicados.
        
        Args:
            mensajes (list): Lista de mensajes originales.
        
        Returns:
            list: Lista de mensajes procesados con datos clave.
        """
        mensajes_procesados = {}
        
        for mensaje in mensajes:
            # Extraer campos relevantes
            id_mensaje = mensaje['id']
            fecha_envio = mensaje['message_date'].get('created')
            remitente = mensaje['from']['user_id']
            destinatario = mensaje['to']['user_id']
            texto = mensaje['text']
            
            # Usar el ID o la fecha como clave para evitar duplicados
            clave_unica = id_mensaje or fecha_envio
            
            # Si ya existe este mensaje, ignorarlo
            if clave_unica in mensajes_procesados:
                continue
            
            # Guardar mensaje procesado
            mensajes_procesados[clave_unica] = {
                'id': id_mensaje,
                'fecha_envio': fecha_envio,
                'remitente': remitente,
                'destinatario': destinatario,
                'texto': texto
            }
        
        # Retornar los valores únicos como lista
        return list(mensajes_procesados.values())


    
    def registrar_pago(self, invoice):
        """
        Registra un pago para una factura específica.

        :param invoice: Registro de la factura (account.move) a pagar.
        """
        try:
            # Registrar el pago de la factura
            payment = self.env['account.payment.register'].with_context(
                active_model='account.move',
                active_ids=invoice.ids
            ).create({
                'amount': invoice.amount_residual,  # Monto pendiente de la factura
                'journal_id': self.env['account.journal'].search([('type', '=', 'cash')], limit=1).id,  # Diario de efectivo
                'payment_date': fields.Date.context_today(self),  # Fecha actual
            })
            payment._create_payments()  # Procesar y registrar el pago
            _logger.info(f"Pago registrado y conciliado para la factura {invoice.id}.")
            return payment
        except Exception as e:
            _logger.error(f"Error al registrar el pago para la factura {invoice.id}: {str(e)}", exc_info=True)
            raise
        

    def action_open_import_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'import.excel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': 'Import Excel Data',
        }


                      
    def import_excel(self, headers):
        _logger.info("EXCEL")
        site_id = self.vex_instance_id.meli_country
        if site_id=='MLM':
            model = 'import.excel.wizard'
        elif site_id == 'MLA':
            model = 'import.excel.wizard.mla'
        return {
            'type': 'ir.actions.act_window',
            'res_model': model,
            'view_mode': 'form',
            'target': 'new',
            'name': 'Import Excel Data',
        }



   
    def synchronize_specific_category(self, category_id, headers):
        """
        Sincroniza una categoría específica desde Mercado Libre, incluyendo su jerarquía de padres e hijos.
        """
        _logger.info("Iniciando sincronización de la categoría específica con ID: %s", category_id)

        current_user = self.env.user
        instance_id = self.vex_instance_id if self.vex_instance_id else current_user.meli_instance_id

        if not instance_id:
            _logger.error("No se encontró una instancia de Mercado Libre en self ni en current_user.")
            raise UserError("No se encontró una instancia de Mercado Libre para sincronizar.")

        # Cache para evitar solicitudes y creaciones redundantes
        processed_categories = {}

        def fetch_category_details(cat_id):
            """Obtiene los detalles de una categoría desde la API de Mercado Libre."""
            url = f"https://api.mercadolibre.com/categories/{cat_id}"
            _logger.debug("Obteniendo detalles de la categoría desde URL: %s", url)
            try:
                response = requests.get(url, headers=headers, timeout=20)
                if response.status_code == 200:
                    return response.json()
                else:
                    _logger.error("No se pudo obtener la categoría con ID: %s. Código de estado: %s", cat_id, response.status_code)
                    raise UserError(f"No se pudo obtener la categoría {cat_id}. Código de estado: {response.status_code}")
            except requests.RequestException as req_err:
                _logger.error("Error de conexión al obtener la categoría %s: %s", cat_id, req_err)
                raise UserError(f"Error de conexión al obtener la categoría {cat_id}: {req_err}")

        def create_or_update_category(data, parent_id=None):
            """Crea o actualiza una categoría en Odoo."""
            category_id = data.get('id')
            if not category_id:
                _logger.warning("Datos inválidos de categoría (sin ID): %s", data)
                return None

            if category_id in processed_categories:
                return processed_categories[category_id]

            _logger.debug("Procesando categoría: %s con parent_id: %s", category_id, parent_id)

            existing_category = self.env['product.category'].search([
                ('meli_code', '=', category_id)
            ], limit=1)

            if not existing_category:
                _logger.info("Creando nueva categoría: %s", data.get('name'))
                new_category = self.env['product.category'].sudo().create({
                    'name': data.get('name'),
                    'meli_code': category_id,
                    'server_meli': True,
                    'parent_id': parent_id,
                    'instance_id': instance_id.id
                })
                processed_categories[category_id] = new_category
                return new_category
            else:
                _logger.debug("Categoría existente encontrada: %s", existing_category.id)
                processed_categories[category_id] = existing_category
                return existing_category

        try:
            # 1. Obtener detalles de la categoría objetivo
            category_data = fetch_category_details(category_id)

            # 2. Procesar la jerarquía de padres (ascendente)
            parent_stack = category_data.get('path_from_root', [])
            parent_id = None

            for parent in parent_stack:
                parent_data = fetch_category_details(parent['id'])
                parent_record = create_or_update_category(parent_data, parent_id=parent_id)
                parent_id = parent_record.id  # Para el siguiente nivel en la jerarquía

            # 3. Crear o actualizar la categoría actual
            category_record = create_or_update_category(category_data, parent_id=parent_id)

            # 4. Procesar las subcategorías (hijos directos)
            for child in category_data.get('children_categories', []):
                child_data = fetch_category_details(child['id'])
                create_or_update_category(child_data, parent_id=category_record.id)

            _logger.info("Sincronización completada para la categoría específica ID: %s", category_id)

        except Exception as ex:
            _logger.error("Error al sincronizar la categoría específica ID %s: %s", category_id, ex)
            raise UserError(f"Error al sincronizar la categoría específica: {str(ex)}")

    def synchronize_category(self, headers):
        """Sincroniza las categorías desde MercadoLibre."""
        url = f"https://api.mercadolibre.com/sites/{self.vex_instance_id.meli_country}/categories"
        _logger.info("Iniciando sincronización de categorías desde URL: %s", url)
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                _logger.error("Respuesta inválida, código de estado: %s", response.status_code)
                raise UserError("Credenciales inválidas o respuesta no válida.")

            categories = response.json()
            category_count = 0
            processed_categories = {}  # Cache para reducir queries repetidas

            def process_category(data, parent_id=None):
                """Procesa una categoría y sus subcategorías."""
                category_id = data.get('id')
                if not category_id:
                    return None

                # Revisar si ya fue procesada antes en la sesión
                if category_id in processed_categories:
                    return processed_categories[category_id]

                # Buscar categoría existente
                existing_category = self.env['product.category'].search(
                    [('meli_code', '=', category_id)],
                    limit=1
                )

                if not existing_category:
                    new_category = self.env['product.category'].sudo().create({
                        'name': data.get('name'),
                        'meli_code': category_id,
                        'server_meli': True,
                        'parent_id': parent_id,
                        'instance_id': self.vex_instance_id.id
                    })
                    existing_category = new_category

                processed_categories[category_id] = existing_category

                # Obtener subcategorías solo si no se ha procesado antes
                subcategories_url = f"https://api.mercadolibre.com/categories/{category_id}"
                sub_resp = requests.get(subcategories_url, headers=headers, timeout=20)
                
                if sub_resp.status_code == 200:
                    subcategories_data = sub_resp.json().get("children_categories", [])
                    for subcategory in subcategories_data:
                        process_category(subcategory, parent_id=existing_category.id)
                else:
                    _logger.warning("No se pudo obtener subcategorías para categoría: %s", category_id)

                return existing_category

            # Procesar categorías principales (máximo 10)
            for item in categories[:10]:
                process_category(item)
                category_count += 1

            # Actualizar el contador
            vex_product_category = self.env['vex.restapi.list'].search([
                ('model', '=', 'product.category')
            ])
            vex_product_category.write({'last_number_import': category_count})

            _logger.info("Sincronización finalizada. Categorías importadas: %d", category_count)

        except requests.RequestException as req_err:
            _logger.error("Error de conexión o timeout: %s", req_err)
            raise UserError(f"Error de conexión al sincronizar categorías: {req_err}")

        except Exception as ex:
            _logger.error("Error sincronizando categorías: %s", ex)
            raise UserError(f"Error al sincronizar categorías: {str(ex)}")

    def synchronize_unit_category(self, headers, meli_code, instance_id):
        _logger.info("synchronize_unit_category")
        url_son= f"https://api.mercadolibre.com/categories/{meli_code}"
        try:
            response_son = requests.get(url_son, headers=headers)
            if response_son.status_code == 200:
                _logger.info("code 200")
                
                json_obj_son = json.loads(response_son.text)
                padre_parent_id = self.env['product.category'].search([('meli_code', '=', meli_code),('instance_id', '=', instance_id)])
                _logger.info("padre_parent_id %s",padre_parent_id)
                if len(padre_parent_id) > 0:
                    for item in json_obj_son["children_categories"]:
                        parent_id_existing = self.env['product.category'].search([('meli_code', '=', item['id']),('instance_id', '=', instance_id)])
                        if len(parent_id_existing) == 0:
                            son_parent_id = self.env['product.category'].sudo().create({
                                'name': item['name'],
                                'meli_code': item['id'],
                                'server_meli': True,
                                'parent_id': padre_parent_id.id,
                                'instance_id': instance_id
                            })
                else:
                    categ = self.env['product.category'].sudo().create({
                                'name': json_obj_son['name'],
                                'meli_code': json_obj_son['id'],
                                'server_meli': True,
                                'parent_id': None,
                                'instance_id': instance_id
                            })
                    _logger.info("categ %s",categ)
                    
        except Exception as ex:
            _logger.info("Exception %s", ex)
            
    def get_product_sku(self, data, headers):
        limit = 100  # Límite máximo permitido por la API
        scroll_id = None  # Inicialmente no hay scroll_id

        while True:
            # Construir la URL dependiendo de si ya tenemos un scroll_id o no
            if scroll_id:
                url_sku = f"https://api.mercadolibre.com/users/{data}/items/search?search_type=scan&scroll_id={scroll_id}&limit={limit}"
            else:
                url_sku = f"https://api.mercadolibre.com/users/{data}/items/search?search_type=scan&limit={limit}"

            try:
                # Hacer la petición a la API de Mercado Libre
                response = requests.get(url_sku, headers=headers)
                
                if response.status_code == 200:
                    _logger.info("SI MANDA REQUESRT")
                    json_sku = json.loads(response.text)
                    results = json_sku.get('results', [])
                    scroll_id = json_sku.get('scroll_id')  # Obtener el nuevo scroll_id
                    
                    if not results:
                        _logger.info("No hay más resultados disponibles.")
                        break  # Salir del bucle si no hay más resultados

                    # Procesar los resultados en bloques de 20
                    result_parts = [results[i:i + 20] for i in range(0, len(results), 20)]

                    for i, part in enumerate(result_parts, start=1):
                        _logger.info(f"DESCRIPTION: {','.join(part)}")
                        _logger.info(f"PART: {part}")
                        new_import_line = self.env['vex.import_line'].create({
                            'description': ','.join(part),
                            'status': 'pending',
                            'instance_id': self.vex_instance_id.id,
                            'stock_import': self.stock_import,
                            'images_import': self.import_images,
                            'action': 'product',
                        })

                    _logger.info(f"Se procesaron {len(results)} productos en este bloque.")
                    
                    # Verificar si el scroll_id es nulo, lo que indica que no hay más páginas disponibles
                    if not scroll_id:
                        _logger.info("Se alcanzó el final de la lista de productos.")
                        break
                else:
                    _logger.warning(f"Error en la respuesta de la API: {response.text}")
                    break  # Salir del bucle si hay un error en la respuesta

            except Exception as e:
                _logger.error(f"Error durante la obtención de productos: {str(e)}")
                break  # Salir del bucle si ocurre una excepción




   
    def get_product_item(self, sku, headers):    
        try:
            self.vex_instance_id.get_access_token()
            vex_synchro = self.env['vex.synchro']
            url_item = f"https://api.mercadolibre.com/items?ids={sku}"
            _logger.info(url_item)
            response_item = requests.get(url_item, headers=headers)
            start_time = datetime.today()
            log_product_id = vex_synchro.create_log(sku)
            state = True
            msg = ""
            if response_item.status_code == 200:
                items = json.loads(response_item.text)
                for item in items:
                    if item['code'] != 200:
                        msg = f"Request error: {item['code']}"
                        _logger.warning(msg)
                        state = False
                        log_product_id.write({'state': 'error', 'description': msg})
                        return
                    
                    item_data = item['body']
                    existing_product_id = self._find_existing_product(item_data['id'], self.vex_instance_id.id)
                    _logger.info('existing_product_id%s',existing_product_id)
                    attributes, ml_reference = self._process_attributes(item_data['attributes'])
                    _logger.info('Returned attributes: %s, ml_reference: %s', attributes, ml_reference)
                    attribute_value_tuples = self._create_or_update_attributes(attributes, self.vex_instance_id.id)
                    _logger.info('attribute_value_tuples%s',attribute_value_tuples)
                    image_1920 = None 
                    if self.import_images and item_data['pictures']:
                        image_url = item_data['pictures'][0]['url']
                        image_content = requests.get(image_url).content
                        if image_content:
                            image_1920 = base64.b64encode(image_content).decode('utf-8')
                    category_id = self._ensure_category(item_data['category_id'], headers, self.vex_instance_id.id)
                    _logger.info('category_id%s',category_id)

                    sku_id = self._get_or_create_sku(ml_reference, self.vex_instance_id.id)
                    _logger.info('sku_id%s',sku_id)
                    stock_location_obj = self._get_stock_location(item_data['shipping']['logistic_type'])
                    _logger.info('stock_location_obj%s',stock_location_obj)
                    marketplace_fee = self._get_marketplace_fee(headers, item_data['price'], item_data['listing_type_id'], item_data['category_id'], self.vex_instance_id.id)
                    _logger.info('marketplace_fee%s',marketplace_fee)
                    _logger.info(1)
                    product_values = {
                        'categ_id': category_id.id,
                        'name': item_data['title'],
                        'list_price': item_data['price'],
                        'mercado_libre_price': item_data['price'],
                        'meli_code': item_data['id'],
                        'default_code': item_data['id'],
                        'server_meli': True,
                        'detailed_type': 'product',
                        'image_1920': image_1920,
                        'ml_reference': ml_reference,
                        'ml_publication_code': item_data['id'],
                        'meli_category_code': item_data['category_id'],
                        'meli_status': item_data['status'],
                        'attribute_line_ids': attribute_value_tuples,
                        'sku_id': sku_id.id if sku_id else False,
                        'listing_type_id': item_data['listing_type_id'],
                        'condition': item_data['condition'],
                        'permalink': item_data['permalink'],
                        'thumbnail': item_data['thumbnail'],
                        'buying_mode': item_data['buying_mode'],
                        'inventory_id': item_data.get('inventory_id'),
                        'action_export': 'edit',
                        'instance_id': self.vex_instance_id.id,
                        'stock_type': stock_location_obj,
                        'upc': next((attr['value_name'] for attr in item_data['attributes'] if attr['id'] == 'GTIN'), None),
                        'store_type': 'mercadolibre',
                        'market_fee': marketplace_fee
                    }
                    _logger.info('product_values%s',product_values)
                    if existing_product_id:
                        msg = "Actualizando producto"
                        existing_product_id.write({'attribute_line_ids': [(5, 0, 0)]})
                        existing_product_id.write(product_values)
                    else:
                        msg = "Creando producto"
                        existing_product_id = self.env['product.template'].create(product_values)
                    _logger.info(msg)
                    self._create_or_update_group_product(existing_product_id, item_data, category_id,
                                            sku_id, ml_reference, image_1920, self.vex_instance_id.id)
                    if self.stock_import:
                        self._update_stock(existing_product_id, item_data)
                    _logger.info(2)
                    log_product_id.write({
                        'state': 'done' if state else 'error',
                        'start_date': start_time,
                        'end_date': datetime.today(),
                        'description': msg
                    })
                    _logger.info(3)
                    """ if item['code'] == 200: 
                        if item['body']['status'] == 'active':
                            existing_product_id = self.env['product.template'].search([('meli_code', '=', item['body']['id']), ('active', '=', True)])

                            ml_reference = None
                            image_1920 = None  

                            # Buscando SELLER_SKU
                            for product in item['body']['attributes']:
                                if product['id'] == 'SELLER_SKU':
                                    ml_reference = product['value_name']
                                    break
                                        
                            if self.import_images and item['body']['pictures']:
                                image_url = item['body']['pictures'][0]['url']
                                image_content = requests.get(image_url).content
                                if image_content:
                                    image_1920 = base64.b64encode(image_content).decode('utf-8')

                            existing_category_id = self.env['product.category'].search([('meli_code', '=', item['body']['category_id'])])      

                            obj = {}
                            
                            obj['categ_id'] = existing_category_id.id if existing_category_id  else self.env.ref('odoo-mercadolibre.category_not_found').id
                            obj['name']= item['body']['title']
                            obj['list_price']= item['body']['price']
                            obj['meli_code']= item['body']['id']
                            obj['default_code']= item['body']['id']
                            obj['server_meli']=True
                            obj['detailed_type']= 'product'
                            obj['image_1920'] = image_1920
                            obj['ml_reference']= ml_reference
                            obj['ml_publication_code']= item['body']['id']
                            obj['meli_category_code']=item['body']['category_id']
                            obj['action_export']='edit'
                            obj['instance_id'] = self.vex_instance_id.id

                            if existing_product_id:
                                existing_product_id.write(obj)
                            else:
                                existing_product_id = self.env['product.template'].create(obj)
                            
                            if self.stock_import:
                                stock_qty = item['body']['available_quantity']
                                product_id=self.env['product.product'].search([('product_tmpl_id','=',existing_product_id.id),('active','=',True)])
                                self._create_or_update_stock(product_id, stock_qty)
                    else:
                        _logger.info(f"ERROR {response_item.text}") """
            else:
                _logger.info(response_item.text)
        except Exception as ex:
            pass
    
    def _find_existing_product(self, meli_code, instance_id):
        return self.env['product.template'].search([
            ('meli_code', '=', meli_code),
            ('instance_id', '=', instance_id)
            #,('active', '=', True)
        ], limit=1)
    
    def _process_attributes(self, attributes_list):
        attributes = []
        ml_reference = None

        for product in attributes_list:
            if product['id'] == 'SELLER_SKU':
                ml_reference = product['value_name']
            else:
                attributes.append({
                    'name': product['name'],
                    'meli_code': product['id'],
                    'value_name': product['value_name']
                })
        _logger.info('attributes %s',attributes)
        _logger.info(' ml_reference%s',ml_reference)
        return attributes, ml_reference
    
    def _create_or_update_attributes(self, attributes, instance_id):
        attribute_value = []

        for attr in attributes:
            attribute = self.env['product.attribute'].search([
                ('meli_code', '=', attr['meli_code']),
                ('instance_id', '=', instance_id)
            ], limit=1)

            if not attribute:
                attribute = self.env['product.attribute'].create({
                    'name': attr['name'],
                    'meli_code': attr['meli_code'],
                    'instance_id': instance_id
                })

            if attr['value_name']:
                value = self.env['product.attribute.value'].search([
                    ('name', '=', attr['value_name']),
                    ('attribute_id', '=', attribute.id),
                    ('instance_id', '=', instance_id)
                ], limit=1)

                if not value:
                    value = self.env['product.attribute.value'].create({
                        'name': attr['value_name'],
                        'attribute_id': attribute.id,
                        'instance_id': instance_id
                    })

                attribute_value.append((attribute.id, value.id))

        return [(0, 0, {'attribute_id': attr_id, 'value_ids': [(6, 0, [val_id])]}) for attr_id, val_id in attribute_value] if attribute_value else False
    
    def _ensure_category(self, category_id, headers, instance_id):
        category = self.env['product.category'].search([
            ('meli_code', '=', category_id),
            ('instance_id', '=', instance_id)
        ], limit=1)

        if not category:
            _logger.info(f"Categoría {category_id} no existe. Creándola...")
            #wizard = self.env['vex.import.wizard']
            _logger.info(f"headers {headers} no existe. Creándola...")
            _logger.info(f"instance_id {instance_id} no existe. Creándola...")
            self.synchronize_unit_category(headers, category_id, instance_id)
            category = self.env['product.category'].search([
                ('meli_code', '=', category_id),
                ('instance_id', '=', instance_id)
            ], limit=1)

        return category or self.env.ref('odoo-mercadolibre.category_not_found')
    
    def _get_or_create_sku(self, ml_reference, instance_id):
        if not ml_reference:
            return False

        sku = self.env['vex.sku'].search([
            ('name', '=', ml_reference),
            ('instance_id', '=', instance_id)
        ], limit=1)

        return sku or self.env['vex.sku'].create({'name': ml_reference, 'instance_id': instance_id})
    
    def _get_stock_location(self, logistic_type):
        return "FULL Mercado Libre Default" if logistic_type == "fulfillment" else "Default Mercado Libre"
    
    def _create_or_update_group_product(self, existing_product_id, item_data, category_id, sku_id, ml_reference, image_1920, instance_id):
        if not (sku_id and ml_reference):
            return

        group_product = self.env['vex.group_product'].search([
            ('product_id', '=', existing_product_id.id),
            ('instance_id', '=', instance_id)
        ], limit=1)

        group_values = {
            'name': existing_product_id.name,
            'url': item_data['permalink'],
            'num_publication': existing_product_id.meli_code,
            'product_id': existing_product_id.id,
            'image': image_1920,
            'price': existing_product_id.list_price,
            'categ_id': category_id.id,
            'quantity': item_data['available_quantity'],
            'sku_id': sku_id.id,
            'instance_id': instance_id
        }

        if group_product:
            group_product.write(group_values)
        else:
            self.env['vex.group_product'].create(group_values)

    def _update_stock(self, existing_product_id, item_data):
        _logger.info("Actualizando stock")
        stock_qty = item_data['available_quantity']
        logistic_type = item_data['shipping']['logistic_type']
        stock_location = self._get_stock_location(logistic_type)

        product_variant = self.env['product.product'].search([
            ('product_tmpl_id', '=', existing_product_id.id),
            ('active', '=', True)
        ], limit=1)

        if product_variant:
            self._create_or_update_stock(product_variant.id, stock_qty, stock_location, debug=True)

    def _create_or_update_stock(self, product_id, stock_qty, stock_location, debug=False):
        """
        Crea o actualiza el stock de un producto en una ubicación específica.
        Si la ubicación no existe, la crea con el nombre proporcionado.

        :param product_id: ID del producto.
        :param stock_qty: Cantidad de stock a establecer.
        :param stock_location: Nombre de la ubicación donde se debe actualizar/crear el stock.
        :param debug: Si es True, activa los logs para esta función.
        """
        log = _logger.info if debug else lambda *args, **kwargs: None  # Log solo si debug es True

        log("Iniciando proceso para actualizar/crear stock para el producto ID: %s en la ubicación: %s", product_id, stock_location)

        StockQuant = self.env['stock.quant']
        StockLocation = self.env['stock.location']
        Product = self.env['product.product']

        # Verificar si el producto existe
        product = Product.browse(product_id)
        if not product.exists():
            _logger.error("No se encontró un producto con el ID: %s", product_id)  # Siempre log de error
            raise ValueError(f"No se encontró un producto con el ID: {product_id}")

        log("Producto encontrado: %s (ID: %s)", product.name, product.id)

        # Buscar o crear la ubicación
        location = StockLocation.search([('name', '=', stock_location)], limit=1)
        if not location:
            log("La ubicación '%s' no existe. Creándola ahora.", stock_location)
            location = StockLocation.create({
                'name': stock_location,
                'usage': 'internal',
            })
            log("Ubicación creada con éxito: %s (ID: %s)", location.name, location.id)

        location_id = location.id
        log("Ubicación seleccionada: %s (ID: %s)", location.complete_name, location_id)

        # Buscar el stock.quant para el producto y la ubicación
        quant = StockQuant.search([('product_id', '=', product.id), ('location_id', '=', location_id)], limit=1)

        if quant:
            log("Se encontró un stock.quant existente. Actualizando cantidad de %s a %s", quant.quantity, stock_qty)
            quant.quantity = stock_qty
        else:
            log("No se encontró un stock.quant para el producto %s en la ubicación %s. Creando uno nuevo.", product.name, location.complete_name)
            StockQuant.create({
                'product_id': product.id,
                'location_id': location_id,
                'quantity': stock_qty,
            })
            log("Nuevo stock.quant creado para el producto %s con cantidad %s en la ubicación %s.", product.name, stock_qty, location.complete_name)

        log("Proceso de actualización/creación de stock completado con éxito.")
    
    def _get_marketplace_fee(self, headers, price, listing_type_id, category_id, instance_id):
        instance = self.env['vex.instance'].search([('id', '=', instance_id)])
        code_country = instance.meli_country
        url = f"https://api.mercadolibre.com/sites/{code_country}/listing_prices?price={price}&listing_type_id={listing_type_id}&category_id={category_id}"
        _logger.info(url)
        response = requests.get(url, headers=headers)
        market_fee = 0.0
        if response.status_code == 200:
            res_json = json.loads(response.text)
            market_fee = res_json['sale_fee_amount']
        else:
            _logger.info(response.text)
        return market_fee
    
    def get_data_from_api(self, uri, header):
        """
        Función que permite consumir un API RestFUL y devuelve la respuesta en JSON.

        Args:
            uri (str): Endpoint de la API donde se va a hacer la solicitud.
            header (dict): Cabecera con los encabezados necesarios para la solicitud.

        Returns:
            dict: Diccionario con la respuesta en formato JSON, o None si la solicitud falla.
        """
        try:
            #_logger.info(f"PETICION Url: {uri} con los headers: {header}")
            response = requests.get(uri, headers=header)
            #_logger.info(f"Dio respuesta -> {response.text}") RESPUESTA MUY GRANDE

            # Verificar si la respuesta fue exitosa (código 200)
            if response.status_code != 200:
                _logger.error(f"Error en la solicitud a {uri}. Código de estado: {response.status_code}, Respuesta: {response.text}")
                if response.status_code == 401:
                    _logger.error("Need to update token")
                    return 401
                return None  # Devolver None en caso de error para manejarlo en get_customer

            # Intentar decodificar la respuesta como JSON
            json_response = json.loads(response.text)
            return json_response

        except requests.RequestException as e:
            _logger.error(f"Error de conexión al hacer la solicitud a la API: {str(e)} - URI: {uri}")
            return None  # Devolver None si hubo un problema de conexión
        except json.JSONDecodeError as e:
            _logger.error(f"Error al decodificar la respuesta de la API: {str(e)} - URI: {uri}, Respuesta: {response.text}")
            return None  # Devolver None si el JSON no es válido

    def get_customer(self, headers):
        json_user_me = self.get_data_from_api(ME_URI, headers)

        if not json_user_me:
            _logger.error("No se pudo obtener la información del usuario desde la API.")
            return

        if json_user_me.get("status") == 401:
            raise ValidationError("El Token ha caducado, por favor generarlo de nuevo")

        there_is_orders = True
        limit = 50
        current_page = 1
        total_customers_created = 0

        date_init_formatted = str(self.date_from).replace(" ", "T") + '.000-00:00'
        date_end_formatted = str(self.date_to).replace(" ", "T") + '.000-00:00'

        while there_is_orders:
            if total_customers_created >= 1000:
                _logger.info("Se alcanzó el límite de 1000 clientes creados. Finalizando.")
                break

            offset = (current_page - 1) * limit
            url_orders = GET_ORDER.format(json_user_me['id'], date_init_formatted, date_end_formatted, limit, offset)
            json_orders = self.get_data_from_api(url_orders, headers)

            if not json_orders:
                _logger.error(f"No se pudo obtener las órdenes para el offset {offset}. Saliendo del bucle.")
                break

            orders = json_orders.get("results", [])

            if not orders:
                _logger.info("No hay más órdenes disponibles.")
                there_is_orders = False
                break

            order_counter = 0

            for order in orders:
                if order_counter >= 2000 or total_customers_created >= 10000:
                    _logger.info("Límite alcanzado en esta iteración. Saliendo del bucle de órdenes.")
                    break

                url_rut = RUT_URI.format(order["id"])
                json_billing = self.get_data_from_api(url_rut, headers)

                if not json_billing:
                    _logger.error(f"No se pudo obtener información de facturación para la orden {order['id']}. Saltando.")
                    continue

                document_type = json_billing['billing_info'].get('doc_type')
                data_name, data_ruc, data_stree_name, data_stree_number, data_country = "", "", "", "", ""

                # Obtener información adicional de facturación
                for item in json_billing["billing_info"].get("additional_info", []):
                    item_type = item.get("type")
                    item_value = item.get("value")

                    if item_type == "DOC_NUMBER":
                        data_ruc = item_value
                    if document_type == 'DNI':
                        if item_type == "FIRST_NAME":
                            data_name = item_value
                        elif item_type == "LAST_NAME":
                            data_name += f" {item_value}"
                    else:
                        if item_type == "BUSINESS_NAME":
                            data_name = item_value

                    if item_type == "STREET_NAME":
                        data_stree_name = item_value
                    if item_type == "STREET_NUMBER":
                        data_stree_number = item_value
                    if item_type == "COUNTRY_ID":
                        data_country = item_value

                country_id = self.env['res.country'].search([('code', '=', data_country)], limit=1)

                # Procesar datos si se tienen los campos necesarios
                if data_name == "Anónimo":
                    _logger.info("Cliente Anónimo detectado. Saltando.")
                    continue

                if not data_stree_name:
                    _logger.info("No se encontró dirección (street). Saltando.")
                    continue

                data_street = f"{data_stree_name} {data_stree_number}".strip()

                partner_exist = self.env["res.partner"].search([('vat', '=', data_ruc),('instance_id', '=', self.vex_instance_id.id)], limit=1)
                if partner_exist:
                    _logger.info(f"Cliente {data_ruc} ya existe. Omitiendo.")
                    continue

                # Crear el nuevo partner basado en facturación
                obj_customer = {
                    "name": data_name.strip(),
                    "vat": data_ruc,
                    "street": data_street,
                    "l10n_latam_identification_type_id": 1,
                    "server_meli": True,
                    "meli_code": data_ruc,
                    "country_id": country_id.id if country_id else None,
                    "instance_id": self.vex_instance_id.id,
                }

                try:
                    new_partner = self.env['res.partner'].create(obj_customer)
                    if new_partner:
                        total_customers_created += 1
                        _logger.info(f"Cliente creado desde facturación: {data_name} ({total_customers_created}/1000)")
                except Exception as ex:
                    _logger.error(f"Error al crear cliente desde facturación: {ex}")

                # Segundo flujo: obtener y crear cliente basado en datos de la orden
                url_order = f"https://api.mercadolibre.com/orders/{order['id']}"
                json_order = self.get_data_from_api(url_order, headers)

                if not json_order:
                    _logger.error(f"No se pudo obtener información del comprador para la orden {order['id']}.")
                    continue

                buyer_info = json_order.get("buyer", {})
                buyer_id = buyer_info.get("id")
                buyer_nickname = buyer_info.get("nickname", "")
                buyer_first_name = buyer_info.get("first_name", "")
                buyer_last_name = buyer_info.get("last_name", "")

                if not buyer_id or not buyer_nickname:
                    _logger.warning(f"Información incompleta del comprador en la orden {order['id']}.")
                    continue

                meli_partner_exist = self.env["res.partner"].search([('nickname', '=', buyer_nickname),('instance_id', '=', self.vex_instance_id.id)], limit=1)
                if meli_partner_exist:
                    _logger.info(f"Cliente con nickname {buyer_nickname} ya existe. Omitiendo.")
                    continue

                obj_meli_customer = {
                    "name": f"{buyer_first_name} {buyer_last_name}".strip(),
                    "nickname": buyer_nickname,
                    "l10n_latam_identification_type_id": 1,
                    "server_meli": True,
                    "meli_user_id": buyer_id,
                    "instance_id": self.vex_instance_id.id,
                }

                try:
                    new_partner = self.env['res.partner'].create(obj_meli_customer)
                    if new_partner:
                        total_customers_created += 1
                        _logger.info(f"Cliente creado desde comprador de orden: {buyer_nickname} ({total_customers_created}/1000)")
                except Exception as ex:
                    _logger.error(f"Error al crear cliente desde comprador de orden: {ex}")

                order_counter += 1

            current_page += 1

        vex_res_partner = self.env['vex.restapi.list'].search([('model', '=', 'res.partner')])
        vex_res_partner.write({'last_number_import': total_customers_created})
        _logger.info(f"Proceso completado. Total de clientes creados: {total_customers_created}")




   

    
    def get_order(self, headers):
        contador_ordenes = 0
        json_user_me = self.get_data_from_api(ME_URI, headers)

        if json_user_me == 401:
            raise ValidationError("El Token ha caducado, por favor generarlo de nuevo")
        
        # Obtener el rango de fechas (día por día)
        current_date = self.date_from
        end_date = self.date_to
        
        # Calcular el número total de días a procesar
        total_days = (end_date - current_date).days + 1  # +1 para incluir la fecha final
        current_day_count = 1  # Contador de días procesados
        
        limit = 20  # Límite de órdenes por petición
        total_orders = 0  # Total de órdenes procesadas
        
        while current_date <= end_date:
            there_is_orders = True
            current_page = 1
            daily_order_count = 0  # Contador de órdenes por día
            
            # Formatear las fechas para el rango del día actual
            date_init_formatted = current_date.strftime('%Y-%m-%dT00:00:00.000-00:00')
            date_end_formatted = current_date.strftime('%Y-%m-%dT23:59:59.000-00:00')
            
            while there_is_orders:
                offset = (current_page - 1) * limit
                url_orders = GET_ORDER.format(json_user_me['id'], date_init_formatted, date_end_formatted, limit, offset)
                
                try:
                    # Realizar la petición a la API
                    response_item = requests.get(url_orders, headers=headers)
                    response_item.raise_for_status()  # Levanta un error si el código de estado no es 2xx

                    if response_item.status_code == 200:
                        json_orders = json.loads(response_item.text)
                        data = json_orders.get("results", [])

                        if data:
                            order_ids = [order['id'] for order in data]
                            order_str = ','.join(map(str, order_ids))

                            # Crear un nuevo registro en vex.import_line con las órdenes
                            new_import_line = self.env['vex.import_line'].create({
                                'description': order_str,
                                'status': 'pending',
                                'instance_id': self.vex_instance_id.id,
                                'action': 'order'
                            })

                            current_page += 1
                            daily_order_count += len(data)  # Incrementar el contador de órdenes por día
                        else:
                            there_is_orders = False
                    else:
                        _logger.warning(f"Error al obtener órdenes: {response_item.status_code} - {response_item.reason}")
                        there_is_orders = False

                except requests.exceptions.HTTPError as http_err:
                    _logger.error(f"HTTP error al consultar la API: {http_err}")
                    raise ValidationError(f"Error HTTP al consultar la API: {http_err}")
                except requests.exceptions.RequestException as req_err:
                    _logger.error(f"Error en la conexión con la API: {req_err}")
                    raise ValidationError(f"Error en la conexión con la API: {req_err}")
                except Exception as e:
                    _logger.error(f"Error desconocido: {e}")
                    raise ValidationError(f"Se produjo un error inesperado: {e}")

            # Almacenar el total de órdenes
            total_orders += daily_order_count
            
            # Loguear el progreso con la fecha actual
            formatted_date = current_date.strftime('%d/%m/%Y')  # Formato DD/MM/YYYY
            _logger.info(f"Fecha {formatted_date} procesada - Ordenes obtenidas: {daily_order_count}")
           
            
            # Avanzar al siguiente día
            current_date += timedelta(days=1)
            current_day_count += 1  # Incrementar el contador de días procesados

        # Loguear el total de órdenes procesadas al final
        _logger.info(f"Total de órdenes importadas: {total_orders}")



    def get_pricelist(self, headers):
        product_ids = self.env['product.template'].search([('server_meli','=',True)])
        pricelist_instance = self.env['product.pricelist']
        currency_instance = self.env['res.currency']
        product_tmpl_instance = self.env['product.template']

        for product in product_ids:
            url = f"https://api.mercadolibre.com/items/{product.meli_code}/prices"
            pricelist_id = None
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    json_object = json.loads(response.text)
                    for price in json_object['prices']:
                        currency_id = currency_instance.search([('name','=',price['currency_id'])])
                        odoo_listprices = pricelist_instance.search([('name','=',price['type'])])
                        if len(odoo_listprices)==0:
                           pricelist_id= pricelist_instance.create({'name':price['type'], 'currency_id':currency_id.id})
                        else:
                            pricelist_id = odoo_listprices
                        obj ={}
                        obj['meli_id']=price["id"]
                        obj['product_tmpl_id']=product.id
                        obj['min_quantity']=1
                        obj['fixed_price']=price["amount"]
                        obj['date_start']=price["conditions"]["start_time"]
                        obj['date_end']=price["conditions"]["end_time"]
                        obj['pricelist_id']=pricelist_id.id
                        price_item = self.env['product.pricelist.item'].search([('meli_id','=',price["id"])])
                        if len(price_item) == 0:
                            self.env['product.pricelist.item'].create(obj)
                        else:
                            self.env['product.pricelist.item'].write(obj)

            except Exception as ex:
                pass


     # ITEMS

    def get_items_ids_by_seller_id(self, id: int, limit: int = 200) -> list:
        """
        Función para obtener IDs de productos en conjuntos aleatorios usando un offset aleatorio.

        Args:
        - id: ID del vendedor en Mercado Libre.
        - limit: Cantidad máxima de productos a recuperar por cada solicitud.

        Returns:
        - List[str]: Lista de IDs de productos.
        """
        # Definir la URL base para la API de Mercado Libre
        base_url = f"https://api.mercadolibre.com/users/{id}/items/search?limit={limit}"
        headers = {
            'Authorization': f'Bearer {self.vex_instance_id.access_token}'
        }

        # Hacer la primera solicitud para obtener el valor total de artículos
        try:
            response = requests.get(f"{base_url}&offset=0", headers=headers)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            _logger.error(f"Error al obtener el número total de artículos: {str(e)}")
            raise UserError(f"Error al obtener artículos: {str(e)}")

        # Obtener el valor total de artículos del vendedor
        total = data.get('paging', {}).get('total', 0)
        _logger.info(f"Total: {total}")

        # Si no hay artículos, retornar una lista vacía
        if total == 0:
            return []

        # Generar un offset aleatorio dentro del rango permitido (0 a total - limit)
        max_offset = max(0, total - limit)
        offset = random.randint(0, max_offset)
        offset = random.randint(0, max(0, total - limit))

        # Construir la URL con el offset aleatorio
        url = f"{base_url}&offset={offset}"
        _logger.info(f"Consultando desde offset aleatorio: {offset}, con límite de {limit}")

        # Obtener el subconjunto de elementos usando el offset aleatorio
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            items_data = response.json()
        except requests.RequestException as e:
            _logger.error(f"Error al obtener artículos: {str(e)}, URL: {url}, Headers: {headers}")
            raise UserError(f"Error al obtener artículos: {str(e)}")

        # Retornar la lista de IDs obtenidos en el subconjunto
        items = items_data.get('results', [])
        _logger.info(f"Total de artículos encontrados en este subconjunto: {len(items)}")
        
        return items

### QUESTIONS

    
    
    def get_name_by_id(self,from_id):        

        """Obtiene el nickname desde mercado libre para injectarlo a la pregunta"""
        nombre = "UNKNOWN"
        url = f"{MERCADO_LIBRE_URL}/users/{from_id}"
        headers = {
            'Authorization': f'Bearer {self.vex_instance_id.access_token}'
        }

        try:    
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            response = response.json()
            nickname = response["nickname"]
            if nickname:
                return nickname
            else:
                return nombre   
                    
        except requests.RequestException as e:
            #self._log(f"Error al responder la pregunta: {str(e)}", level='error')
            #_logger.info(f"Respuesta de la API: {answered.status_code}")
            #_logger.info(f"Contenido de la respuesta: {answered.text}")
            return "error"
        

    def get_questions_by_item_id(self, item_id: str):
        self.ensure_one()
        url = f"{MERCADO_LIBRE_URL}/questions/search?item={item_id}"
        headers = {
            'Authorization': f'Bearer {self.vex_instance_id.access_token}'
        }

        total = 999999
        offset = 0
        limit = 50  # El límite por consulta a la API, pero queremos solo 15 en total
        questions = []

        # Recolectar solo las primeras 15 preguntas
        while offset < total and len(questions) < 45:
            try:
                response = requests.get(f"{url}&offset={offset}&limit={limit}", headers=headers)
                response.raise_for_status()
            except requests.RequestException as e:
                _logger.error(f"Error al obtener preguntas: {str(e)}")
                return            

            # Parsear respuesta
            questions_data = response.json()
            questions += questions_data.get('questions', [])
            total = questions_data.get('total', 0)
            limit = questions_data.get('limit', 0)
            offset += limit
           # _logger.info(f"Total questions {total} Questio")

            # Detener el bucle si se alcanzan 15 preguntas
            if len(questions) >= 45:
                _logger.info("15 Questions")
                questions = questions[:45]  # Truncar para asegurar máximo 15 preguntas
                break

        # Agregar lógica para asignar 'nickname' a cada pregunta
        if len(questions) > 0:
            for question in questions:
                from_id = question.get('from', {}).get('id')
                if from_id:
                    nickname = self.get_name_by_id(from_id)
                    question['nickname'] = nickname

        _logger.info(f"Questions del item {item_id} retrieved succesfully ,questions -> {len(questions)}")
        return questions if questions else []



    def import_items_questions(self):
        self.ensure_one()
        _logger.info("Iniciando la importación de preguntas desde Mercado Libre")
        items_ids = self.get_items_ids_by_seller_id(self.vex_instance_id.user_id)

        questions = []
        for item_id in items_ids:
            questions += self.get_questions_by_item_id(item_id)

        formatted_questions = [self.format_question(question) for question in questions]
        fsd = ' - '.join(str(item) for item in formatted_questions)
        #self._log("Finalizacion de formateo")
        #self._log(fsd)
 

        
        Questions = self.env['vex.meli.questions']

        _logger.info("Finalizacion de env")
        Questions.sudo().multiple_create_if_not_exists(formatted_questions)

        _logger.info("Importación de preguntas completada.")



    def get_questions(self, headers):
        """
        Punto de entrada para la lógica de obtención de preguntas. Trae solo las de los últimos dos meses.
        """
        _logger.info("QUESTIONS ACTIVADO: Iniciando la obtención de preguntas de los últimos dos meses.")
        seller_id = self.vex_instance_id.user_id
        self.import_recent_questions(seller_id)


    def import_recent_questions(self, seller_id):
        """
        Importa preguntas recientes para un vendedor, dividiendo el rango de la última semana día por día,
        con un límite de 150 preguntas.
        """
        self.ensure_one()
        # Configuración de la API
        base_url = f"{MERCADO_LIBRE_URL}/questions/search?seller_id={seller_id}&api_version=4"
        headers = {'Authorization': f'Bearer {self.vex_instance_id.access_token}'}
        limit = 50  # Límite por consulta según la API
        all_questions = []

        # Calcular las fechas de inicio y fin para la última semana
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # Dividir la última semana en intervalos de 1 día
        current_start = start_date

        while current_start < end_date:
            current_end = current_start + timedelta(days=1)

            _logger.info(f"Procesando preguntas del {current_start.isoformat()} al {current_end.isoformat()}.")

            # Construir la URL con el rango de fechas
            date_from = current_start.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            date_to = current_end.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            url = f"{base_url}&date_from={date_from}&date_to={date_to}&sort_fields=date_created&sort_types=DESC"

            offset = 0

            while True:
                try:
                    # Construir la URL paginada
                    paginated_url = f"{url}&offset={offset}&limit={limit}"
                    response = requests.get(paginated_url, headers=headers)
                    response.raise_for_status()

                    # Parsear la respuesta
                    data = response.json()
                    questions = data.get('questions', [])

                    # Si no hay preguntas, terminar el bucle
                    if not questions:
                        _logger.info("No se encontraron más preguntas en este rango. Finalizando este intervalo.")
                        break

                    # Agregar preguntas al total acumulado
                    all_questions.extend(questions)

                    # Detener si se alcanza el límite de 150 preguntas
                    if len(all_questions) >= 150:
                        _logger.info("Se alcanzó el límite de 150 preguntas. Deteniendo el flujo.")
                        self.process_and_save_questions(all_questions[:150])  # Guardar solo las primeras 150 preguntas
                        return

                    _logger.info(f"Procesadas {len(questions)} preguntas, total acumulado: {len(all_questions)}.")

                    # Avanzar el offset para la siguiente página
                    offset += limit

                    # Si se han recuperado todas las preguntas disponibles, terminar
                    if offset >= data.get('total', 0):
                        break

                    # Pausa para evitar sobrecarga en la API
                    time.sleep(1)

                except requests.RequestException as e:
                    _logger.error(f"Error al obtener preguntas: {str(e)}")
                    break

            # Avanzar al siguiente día
            current_start = current_end

        # Procesar y guardar las preguntas si hay alguna
        if all_questions:
            _logger.info(f"Total de preguntas recopiladas: {len(all_questions)}. Iniciando procesamiento.")
            self.process_and_save_questions(all_questions)
            _logger.info(f"Importación completada: {len(all_questions)} preguntas guardadas.")
        else:
            _logger.info("No se encontraron preguntas recientes para importar.")




    def process_and_save_questions(self, questions):
        """
        Procesa las preguntas y las guarda en la base de datos.
        Retorna un diccionario con el estado de cada pregunta.
        """

        #self.ensure_one()

        _logger.info(f"Procesando {len(questions)} preguntas antes de guardar.")
        results = {
            "created": [],
            "existing": [],
            "errors": []
        }

        formatted_questions = []
        for question in questions:
            try:
                formatted_question = self.format_question(question)
                formatted_questions.append(formatted_question)
            except Exception as e:
                _logger.error(f"Error al formatear la pregunta: {question}. Detalle: {e}")
                results["errors"].append({"question": question, "error": str(e)})

        if formatted_questions:
            _logger.info(f"Guardando {len(formatted_questions)} preguntas en la base de datos.")
            try:
                saved_results = self.env['vex.meli.questions'].sudo().multiple_create_if_not_exists(formatted_questions)
                _logger.info(f"Dio este resultado {saved_results}") 
                for result in saved_results:
                    if result.get("created"):
                        results["created"].append(result)
                    else:
                        results["existing"].append(result)
                _logger.info(f"Enviando estos resultados {saved_results}")
                return saved_results
            except Exception as e:
                _logger.error(f"Error al guardar las preguntas en la base de datos: {e}")
                results["errors"].append({"save_error": str(e)})
        else:
            _logger.info("No hay preguntas formateadas para guardar.")

        return saved_results



    def format_question(self, question: dict):
        """
        Da formato a una pregunta para que sea compatible con la base de datos.
        """
        #self.ensure_one()

        #_logger.info(f"recibiendo pregunta {question}") 
        vex_instance_id = None

        seller_id = str(question.get('seller_id', '')).strip()

        instance = self.env['vex.instance'].sudo().search([('user_id', '=',seller_id )], limit=1)
        _logger.info(f"Buscando instancia, para la pregunta {seller_id}")
   
        if not instance:           
            raise ValueError("No se encontró vex_instance_id y no hay alternativa válida.")

        
        formatted_question = {
            'name': f"Pregunta {question.get('id')}",
            'meli_item_id': question.get('item_id'),
            'meli_seller_id': question.get('seller_id', ''), 
            'meli_status': question.get('status', 'unknown'), 
            'meli_text': question.get('text', ''),  
            'meli_id': question.get('id'),  
            'meli_deleted_from_listing': question.get('deleted_from_listing', False),  
            'meli_hold': question.get('hold', False),  
            'meli_answer': question.get('answer', {}).get('text') if question.get('answer') else None,  
            'meli_from_id': question.get('from', {}).get('id', ''),  
            'meli_import_type': 'product_question', 
            'meli_created_at': datetime.strptime(
                question.get('date_created', '1970-01-01T00:00:00.000Z'),
                '%Y-%m-%dT%H:%M:%S.%f%z'
            ).strftime('%Y-%m-%d %H:%M:%S') if question.get('date_created') else None,  
            'meli_from_nickname': question.get('from', {}).get('nickname', 'Unknown'), 
            'meli_instance_id': instance.id  
        }
        
        # Si la pregunta tiene respuesta, extraemos la fecha de respuesta
        if question.get('answer'):
            formatted_question['meli_answered_at'] = datetime.strptime(
                question['answer'].get('date_created', '1970-01-01T00:00:00.000Z'),
                '%Y-%m-%dT%H:%M:%S.%f%z'
            ).strftime('%Y-%m-%d %H:%M:%S') if question['answer'].get('date_created') else None

        return formatted_question
    



    @api.model
    def answer_question(self ,meli_id:str ,response:str,accessToken):
        _logger.info(f"Iniciando la respuesta a la pregunta {meli_id}")
        _logger.info(f"Se supone que aqui sale el token -> {self.vex_instance_id.access_token}")
        _logger.info(f"Recibido -> {accessToken}")

        if accessToken == 0: #Update to work with multi instances
            accessToken = self.env['vex.meli.questions'].sudo().search([('meli_id', '=', meli_id)], limit=1).meli_instance_id.access_token
            

        url = f"{MERCADO_LIBRE_URL}/answers"
        headers = {
            "Authorization": f"Bearer {accessToken}"
        }

        try:
            body = {
                "question_id": meli_id,
                "text": response
            }

            # Agrega logging para depuración
            _logger.info(f"URL de la solicitud: {url}")
            _logger.info(f"Headers de la solicitud: {headers}")
            _logger.info(f"Body de la solicitud: {body}")


            answered = requests.post(url, headers=headers, json=body)
            answered.raise_for_status()
            
            _logger.info(f"Respuesta exitosa")
            _logger.info(f"Respuesta de la API: {answered.status_code}")
            _logger.info(f"Contenido de la respuesta: {answered.text}")

            return True
            
        except requests.RequestException as e:
            _logger.error(f"Error al responder la pregunta: {str(e)}")
            return False
        

    @api.model
    def delete_question(self ,meli_id:str,accessToken):
       
        _logger.info(f"Iniciando eliminacion de la pregunta{meli_id}")

        url = f"{MERCADO_LIBRE_URL}/questions/{meli_id}"
        headers = {
            "Authorization": f"Bearer {accessToken}"
        }

        try:           
            # Agrega logging para depuración
            _logger.info(f"URL de la solicitud: {url}")
            _logger.info(f"Headers de la solicitud: {headers}")           

            response = requests.delete(url, headers=headers)            
            response.raise_for_status()
            
            _logger.info(f"Respuesta exitosa")
            _logger.info(f"Respuesta de la API: {response.status_code}")

            if response.status_code == 200:
                print("Pregunta eliminada correctamente")
                return True
            else:
                print(f"Error al eliminar la pregunta: {response.status_code}, {response.text}")
                return False                                    

        except requests.RequestException as e:
            _logger.error(f"Error al eliminar la pregunta: {str(e)}", level='error')
            return False
     
       

        