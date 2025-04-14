# -*- coding: utf-8 -*-
import logging
import uuid

from werkzeug.utils import redirect
from odoo.exceptions import UserError
from odoo import _, http
from datetime import datetime, timedelta, timezone
import pytz
import base64



import requests
import json
import re
MERCADO_LIBRE_URL = "https://api.mercadolibre.com" 
from odoo.http import request
from openai import OpenAI


_logger = logging.getLogger(__name__)



class MeliController(http.Controller):            
    def handle_items(self,body, instance):
        item_id_regex = r"/items/(\w+)"
        resource = body.get('resource')
        sku = re.search(item_id_regex, resource).group(1)
        
        instance.update_item_by_sku(sku)
    
    def handle_orders(self,body, instance):
        orders_id_regex = r"/orders/(\w+)"
        resource = body.get('resource')
        order_id = re.search(orders_id_regex, resource).group(1)
        order = instance.get_order_by_id(order_id)
        # Here does't exist delete order, because the order is not deleted, only is canceled
        if request.env['sale.order'].sudo().search([('meli_order_id', '=', order_id)]):
            _logger.info(f"Order {order_id} already exists",'info')
            instance.update_order(order)
        else:
            _logger.info(f"Creating order {order_id}", 'info')
            instance.create_order(order)
    

    def limpiar_datos_producto(self,datos_producto):
        # Limpiamos y estructuramos los datos
        producto_limpio = {}

        # Extraemos valores simples
        producto_limpio['ID del producto'] = datos_producto.get('id', 'Desconocido')
        producto_limpio['Nombre del producto'] = datos_producto.get('title', 'Sin nombre')
        producto_limpio['Precio'] = f"{datos_producto.get('price', 0)} {datos_producto.get('currency_id', 'MXN')}"
        producto_limpio['Categoría'] = datos_producto.get('category_id', 'Desconocida')
        producto_limpio['Estado'] = datos_producto.get('condition', 'Desconocido')
        
        producto_limpio['Stock disponible'] = datos_producto.get('available_quantity', '1')
        
        
        # Aseguramos que la información sobre la garantía sea legible
        garantia = datos_producto.get('sale_terms', [])
        producto_limpio['Garantía'] = next((term['value_name'] for term in garantia if term['name'] == 'Tipo de garantía'), 'No especificada')
        
        # Añadimos información de ubicación y envío
        shipping_info = datos_producto.get('shipping', {})
        producto_limpio['Envío gratuito'] = shipping_info.get('free_shipping', 'No disponible')

        # Información adicional
        producto_limpio['Descripcion corta'] = ', '.join(
            [attr['value_name'] or '' for attr in datos_producto.get('attributes', []) if 'value_name' in attr]
        )

        
        # Otras claves importantes
        producto_limpio['URL'] = datos_producto.get('permalink', 'No disponible')

        return producto_limpio

    def handle_questions(self,instance,body):
        meli_question_id = body['resource'].split('/')[-1]
        _logger.info(f"Procesando pregunta ID: {meli_question_id} para instancia: {instance.name}")

        question_json = self.get_question_(meli_question_id, instance.access_token)
        original_question = question_json.get('text')
        item_id_meli = question_json.get('item_id')

        if not original_question or not item_id_meli:
            _logger.info(f"Datos incompletos en la pregunta: {question_json}")
            return

        _logger.info(f"Pregunta recibida: '{original_question}', Item ID: {item_id_meli}")

        datos_producto = self.get_product_info(item_id_meli, instance.access_token,debug=True)
        descripcion_producto = self.get_product_description(item_id_meli, instance.access_token)

        datos_producto_limpio = self.limpiar_datos_producto(datos_producto)
        datos_producto_limpio['descripcion'] = descripcion_producto

        _logger.info(f"Datos procesados del producto: {datos_producto_limpio}")


        if question_json.get('answer') is None:
            texto_de_la_pregunta  = self.clean_text(question_json.get('text'))
            _logger.info(f"Texto USUARIO -> {texto_de_la_pregunta}")
            active_rules = request.env['vex.auto.response'].search([('isRuleActive', '=', True)])

            if active_rules:
            # Si se encuentran reglas, imprimir cada una
                for rule in active_rules:
                    _logger.info(f"userInput: {self.clean_text(rule.userInput)}, autoAnswer: {rule.autoAnswer}, ruleType: {rule.ruleType}")
            else:
                # Si no se encuentran reglas, registrar un mensaje
                _logger.info("No se encontraron reglas activas.")

            rule_responser = self.apply_auto_response_rules(texto_de_la_pregunta)


            ##LOGICA GPT
            config = request.env['vex.gpt.config'].get_gpt_config()
            enable_gpt_responder = config.get('enable_gpt_responder', False)
            chatgpt_key = config.get('chatgpt_key', '')
            client_gpt = OpenAI(api_key = chatgpt_key)

            existing_entry = request.env['vex.prompt.history'].sudo().search([('question_id', '=', meli_question_id)], limit=1)
            if existing_entry:
                    _logger.info(f"Ya existe un registro con question_id {meli_question_id}. No se creará uno nuevo.")
                    return http.Response("OK", status=200, headers={'Content-Type': 'text/plain'})

            
            open_ai=enable_gpt_responder
            if rule_responser != None:
                _logger.info("Respondemos con respuesta de regla!")
                self.answer_question_(meli_question_id,rule_responser,instance.access_token)

            elif open_ai:
                _logger.info("Ninguna regla aplicable, respondiendo con Open AI")

                ## iniciando sesion openAI            
                respuesta_gpt = self.responder_pregunta_producto(original_question,datos_producto_limpio,client_gpt)
                _logger.info(f"LA IA RESPONDERA CON ESTO ---> {respuesta_gpt}")

                if 'Una disculpa,' in respuesta_gpt:
                    _logger.info("Se detecto que la IA no tiene suficiente informacion, pasando pregunta a responder manualmente")
                    self.create_question_and_notify_responders(question_json)
                    return 'OK'
                
                self.answer_question_(meli_question_id,respuesta_gpt,instance.access_token)

                admin_user_id = request.env.ref('base.user_admin').id
                # Cambia temporalmente el entorno al usuario administrador
                request.env = request.env(user=admin_user_id)
                                                           
                history_entry = request.env['vex.prompt.history'].sudo().create({
                    'item_id': item_id_meli,
                    'question_id': meli_question_id,
                    'question_text': original_question,
                    'instance_id': instance.id,
                    'is_answered': False,  # Inicialmente no respondida
                    'gpt_response': respuesta_gpt,
                })
                _logger.info(f"Nuevo registro creado en vex.prompt.history: {history_entry.id}")
                return "OK GPT"
            elif not open_ai:
                self.create_question_and_notify_responders(question_json)                 
        
        return 'OK'
    
    def create_question_and_notify_responders(self, question_json):
        _logger.info("This question will be saved and notified to the responders group.")   
        # Here, we save the answer in the database, to PENDING and then send a notification trough the mail.system from odoo, to give a notification to the 
        # Group of users in charge of answer this question
        _logger.info(f"Vamos a formatear estos datos {question_json}")
        
        #Here we save the question in the sistem
        vex_wizard = request.env['vex.import.wizard'].sudo().search([], limit=1)
        if not vex_wizard:
            vex_wizard = request.env['vex.import.wizard']

        save_question = vex_wizard.process_and_save_questions([question_json])

        #save_question = request.env['vex.import.wizard'].sudo().process_and_save_questions([question_json])
        _logger.info(f"WH recibimos esto. {save_question}")

        # Here we send the notification to the users in charge of answer the question   }

        if save_question['created']:
            question_id = question_json.get('id')
            _logger.info("Nueva pregunta creada. Se notificará a los usuarios.")
            self.notify_question_responders(f"Nueva pregunta en Mercado Libre-{question_id}", "Se ha recibido una nueva pregunta en Mercado Libre. Por favor, revisa el panel de preguntas para responderla.")

        elif save_question['existing']:
            _logger.info("Pregunta ya existente. No se creará un nuevo registro.")
          
       # elif save_question['errors']:

        #self.notify_question_responders("Nueva pregunta en Mercado Libre", "Se ha recibido una nueva pregunta en Mercado Libre. Por favor, revisa el panel de preguntas para responderla.")
                                

    
    
    def notify_question_responders(self, subject, message):
        """Gestionar el canal y notificar a los usuarios"""
        # Buscar usuarios con is_question_responder=True
        responders = request.env['res.users'].sudo().search([('is_question_responder', '=', True)])

        # Crear o obtener el canal
        channel_name = "Questions for Mercado Libre"
        channel = self.create_or_get_channel(channel_name)

        # Agregar usuarios al canal
        self.add_users_to_channel(channel, responders)

        # Enviar el mensaje al canal
        self.notify_channel(channel, subject, message)


    def create_or_get_channel(self, channel_name):
        """Crea un canal si no existe y devuelve el canal"""
        # Buscar el canal por nombre
        channel = request.env['discuss.channel'].sudo().search([('name', '=', channel_name)], limit=1)
        if not channel:
            # Crear el canal si no existe
            channel = request.env['discuss.channel'].sudo().create({
                'name': channel_name,
                'channel_type': 'channel',  # Tipo de canal
                'uuid': self.generate_uuid(),  # Método para generar un UUID único si es necesario
                'active': True,               # Hacer el canal activo
                'group_public_id': 1,         # ID para usuarios internos
            })
            _logger.info(f"Canal creado: {channel_name}")
        return channel

    def add_users_to_channel(self, channel, responders):
        """Agregar usuarios al canal en discuss_channel_member"""
        # Verificar que el modelo discuss_channel_member existe
        MemberModel = request.env['discuss.channel.member'].sudo()
        
        for responder in responders:
            if responder.partner_id:  # Verificar que el usuario tenga un partner asociado
                # Verificar si ya existe el miembro en el canal
                existing_member = MemberModel.search([
                    ('channel_id', '=', channel.id),
                    ('partner_id', '=', responder.partner_id.id)
                ], limit=1)

                if not existing_member:
                    # Crear un nuevo registro en discuss_channel_member
                    MemberModel.create({
                        'channel_id': channel.id,
                        'partner_id': responder.partner_id.id,
                        'custom_channel_name': '',  # Dejar vacío o personalizar según sea necesario
                        'fold_state': 'open',      # Asumimos 'open' como estado visual inicial
                        'is_minimized': False,     # El canal no está minimizado al inicio
                        'is_pinned': False,        # El canal no está anclado por defecto
                    })
                    _logger.info(f"Usuario agregado al canal: {responder.name}")
                else:
                    _logger.info(f"Usuario ya está en el canal: {responder.name}")

        _logger.info(f"Usuarios procesados para agregar al canal: {len(responders)}")

    def notify_channel(self, channel, subject, message):
        """Enviar un mensaje al canal"""
        channel.message_post(
            subject=subject,
            body=message,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        _logger.info(f"Mensaje enviado al canal: {channel.name}")


    def generate_uuid(self):
        """Generar un UUID único para el canal"""
        import uuid
        return str(uuid.uuid4())
    

    def update_stock(self,instance,body):
        _logger.info(f"instancia : {instance.app_id} y el body {body}")
        site_id = instance.meli_country
        resource = body['resource']
        if site_id == 'MLM':
            mlm_id = re.search(r'MLM\w+', resource).group()
        if site_id == 'MLA':
            mlm_id = re.search(r'MLA\w+', resource).group()            
        _logger.info(f"Aqui se actualizara el stock del producto {mlm_id}")
        datos_producto = self.get_product_info(mlm_id,instance.access_token)
        _logger.info(f"Datos del productos -> {datos_producto} ")
        available_quantity = datos_producto.get("available_quantity", None)

        admin_user_id = request.env.ref('base.user_admin').id
        # Cambia temporalmente el entorno al usuario administrador
        request.env = request.env(user=admin_user_id)


        product = request.env['product.product'].search([('default_code', '=', mlm_id)], limit=1)
        _logger.info(f"AVQ -> {available_quantity}  product -> {product.stock_type}")

        #modify_stock = request.env['vex.auto.response']

        product_id = product.id # Reemplaza con el ID real
        stock_qty = available_quantity
        stock_location = product.stock_type

        vex_synchro = request.env['vex.synchro']
        vex_synchro._create_or_update_stock(product_id, stock_qty, stock_location , debug=True)
                                                                
        return 'OK'       

    def responder_pregunta_producto(self, pregunta, datos_producto,client_gpt):
        client = client_gpt
        # Estructuramos los datos del producto como parte del contexto
        contexto_producto = "\n".join([f"{k}: {v}" for k, v in datos_producto.items()])
        
        # Creamos el prompt con el contexto del producto
        prompt = f"""
        Eres un asistente experto para nuestra tienda de mercado libre ademas eres amable y ayudas a responder preguntas de los usuarios sobre nuestros productos para que compren
        . Utiliza la información proporcionada del producto para responder de manera clara, concisa y humana. 
        Ya que respondes preguntas por medio de chat, trata de dar una respuesta corta 
        Si no puedes encontrar la respuesta en la información proporcionada, responde con: "Una disculpa," ya agregas mas respuesta de ser necesario

        Condiciones:
        Siempre ofrecemos facturas hasta 31 dias despues efectuada la compra
    

        Información del producto:
        {contexto_producto}

        La pregunta del usuario es:
        {pregunta}

        Por favor, formula tu respuesta de manera que sea útil, profesional y amigable.
        """


        
        # Llamada usando el cliente de OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # o el modelo que estés utilizando
            messages=[
                {"role": "system", "content": "Eres un asistente que ayuda a los usuarios con información de productos en base de datos."},
                {"role": "user", "content": prompt}  # Aquí pasamos el prompt directamente
            ],
            max_tokens=100  # ajusta según el tamaño de respuesta esperada
        )
        response_dict = response.to_dict()  # Convierte el objeto a un diccionario

        # _logger.info(json.dumps(response_dict, indent=4))
        # _logger.info(response)
        tokens_prompt = response_dict["usage"]["prompt_tokens"]
        tokens_completion = response_dict["usage"]["completion_tokens"]

        _logger.info(self.calcular_costo(tokens_prompt,tokens_completion))
        # Respuesta generada
        return response.choices[0].message.content
    


    def calcular_costo(self,tokens_prompt, tokens_completion):
        """
        Calcula el costo en USD de un llamado a la API de OpenAI basado en las tarifas por millón de tokens.
        También genera un texto detallado con el desglose del costo.

        Args:
            tokens_prompt (int): Cantidad de tokens de entrada (prompt).
            tokens_completion (int): Cantidad de tokens de salida (completion).

        Returns:
            str: Texto detallado con el desglose del costo y el total.
        """
        # Tarifas por 1,000 tokens
        costo_prompt_por_mil = 0.0025  # $2.50 / 1M tokens
        costo_completion_por_mil = 0.01  # $10.00 / 1M tokens

        # Cálculo del costo
        costo_prompt = (tokens_prompt / 1000) * costo_prompt_por_mil
        costo_completion = (tokens_completion / 1000) * costo_completion_por_mil
        costo_total = costo_prompt + costo_completion

        # Generar texto detallado
        texto_detallado = (
            f"Desglose del costo del llamado a la API:\n"
            f"- Tokens de entrada (Prompt): {tokens_prompt} tokens\n"
            f"  * Tarifa: ${costo_prompt_por_mil:.4f} por 1,000 tokens\n"
            f"  * Costo: ${costo_prompt:.6f} USD\n"
            f"- Tokens de salida (Completion): {tokens_completion} tokens\n"
            f"  * Tarifa: ${costo_completion_por_mil:.4f} por 1,000 tokens\n"
            f"  * Costo: ${costo_completion:.6f} USD\n"
            f"\nCosto total del llamado: ${costo_total:.6f} USD"
        )

        return texto_detallado

    def apply_auto_response_rules(self,text):
    # Buscar todas las reglas activas
        active_rules = request.env['vex.auto.response'].search([('isRuleActive', '=', True)])
        
        # Recorrer cada regla activa
        for rule in active_rules:
            # Comprobar el tipo de regla y aplicar la lógica correspondiente
            if rule.ruleType == 'contains' and self.clean_text(rule.userInput) in text:
                _logger.info(f"Regla aplicada: contains. Respuesta: {rule.autoAnswer}")
                return rule.autoAnswer
            elif rule.ruleType == 'exact' and self.clean_text(rule.userInput) == text:
                _logger.info(f"Regla aplicada: exact. Respuesta: {rule.autoAnswer}")
                return rule.autoAnswer
            elif rule.ruleType == 'ends_with' and text.endswith(self.clean_text(rule.userInput)):
                _logger.info(f"Regla aplicada: ends_with. Respuesta: {rule.autoAnswer}")
                return rule.autoAnswer
            elif rule.ruleType == 'starts_with' and text.startswith(self.clean_text(rule.userInput)):
                _logger.info(f"Regla aplicada: starts_with. Respuesta: {rule.autoAnswer}")
                return rule.autoAnswer
        
        # Si no se encuentra ninguna regla aplicable, retornar un mensaje predeterminado
        _logger.info("No se encontró ninguna regla aplicable.")
        return None
    

    def get_product_description(self, meli_product_id: str, accessToken: str, debug: bool = False):
        def log(message, level="info"):
            if debug:
                log_func = getattr(_logger, level, _logger.info)
                log_func(message)

        log(f"Iniciando la obtención de la información del producto {meli_product_id}")
        
        url = f"{MERCADO_LIBRE_URL}/items/{meli_product_id}/description"
        headers = {
            "Authorization": f"Bearer {accessToken}"
        }

        try:
            log(f"URL de la solicitud: {url}")
            log(f"Headers de la solicitud: {headers}")

            # Realizar la solicitud GET para obtener la información del producto
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            log(f"Producto obtenido exitosamente")
            log(f"Respuesta de la API: {response.status_code}")
            log(f"Contenido de la respuesta: {response.text}")
            
            # Retorna la respuesta en formato JSON para utilizarla posteriormente
            res = response.json()
            return res.get('plain_text')
        except requests.exceptions.RequestException as e:
            log(f"Error al obtener la información del producto: {e}", level="error")
            return None

    def get_product_info(self, meli_product_id: str, accessToken: str, debug: bool = False):
        def log_debug(message: str):
            if debug:
                _logger.info(message)

        log_debug(f"Iniciando la obtención de la información del producto {meli_product_id}")
        
        url = f"{MERCADO_LIBRE_URL}/items/{meli_product_id}"
        headers = {
            "Authorization": f"Bearer {accessToken}"
        }

        try:
            log_debug(f"URL de la solicitud: {url}")
            log_debug(f"Headers de la solicitud: {headers}")

            # Realizar la solicitud GET para obtener la información del producto
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            log_debug(f"Producto obtenido exitosamente")
            log_debug(f"Respuesta de la API: {response.status_code}")
            log_debug(f"Contenido de la respuesta: {response.text}")
            
            # Retorna la respuesta en formato JSON para utilizarla posteriormente
            return response.json()

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error al obtener la información del producto: {e}")
            return None
    
    def get_question_(self, meli_question_id: str, accessToken: str, debug: bool = False):
        if debug:
            _logger.info(f"Iniciando la obtención de la pregunta {meli_question_id}")
            
        url = f"{MERCADO_LIBRE_URL}/questions/{meli_question_id}"
        headers = {
            "Authorization": f"Bearer {accessToken}"
        }

        try:
            # Log de debug para solicitud
            if debug:
                _logger.info(f"URL de la solicitud: {url}")
                _logger.info(f"Headers de la solicitud: {headers}")

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            if debug:
                _logger.info(f"Pregunta obtenida exitosamente")
                _logger.info(f"Respuesta de la API: {response.status_code}")
                _logger.info(f"Contenido de la respuesta: {response.text}")
            
            # Retorna la respuesta en formato JSON
            return response.json()

        except requests.exceptions.RequestException as e:
            if debug:
                _logger.error(f"Error al obtener la pregunta: {e}")
            return None
    
   
    def answer_question_(self ,meli_id:str ,response:str,accessToken):
       
        _logger.info(f"Iniciando la respuesta a la pregunta {meli_id}")

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
            _logger.info(f"Error al responder la pregunta: {str(e)}")
            # Agrega logging para verificar la respuesta
            _logger.info(f"Respuesta de la API: {answered.status_code}")
            _logger.info(f"Contenido de la respuesta: {answered.text}")
            return False
        self._log(f"Respuesta a la pregunta {meli_id} enviada correctamente.")

    @http.route('/meli/testser', type='http', auth='public', website=True, csrf=False)
    def meli_webhook_tests(self, **kwargs):
        try:
            # Obtener los datos JSON del cuerpo de la solicitud
            body = request.get_json_data()
            topic = body.get('topic')           
            _logger.info(f"WEBHOOK RECIBIDO DESARROLLO ----------- {topic}   {body.get('attempts')}")
            instance = request.env['vex.instance'].sudo().search([('app_id', '=', body.get('application_id'))], limit=1)
            
             
            if body.get('topic') == 'questions':
                _logger.info(f"Pregunta para la instancia: {instance.name}")
                _logger.info(f"Pregunta detectada -->  {body}")
                meli_question_id = body['resource'].split('/')[-1]
                result = self.get_question_(meli_question_id, instance.access_token)
                if not result:
                    _logger.info("Pregunta eliminada")
                    return http.Response("OK", status=200, headers={'Content-Type': 'text/plain'})

                original_question = result.get('text')
                _logger.info(f"El usuario a preguntado -> {original_question}")
                item_id_meli = result.get('item_id')
                #_logger.info(f"ITEM ID ->  {item_id_meli} ")
                datos_producto = self.get_product_info(item_id_meli,instance.access_token)
                datos_producto_limpio = self.limpiar_datos_producto(datos_producto)
                descripcion_producto = self.get_product_description(item_id_meli,instance.access_token)
                datos_producto_limpio['descripcion larga'] = descripcion_producto
                
                _logger.info(f"Datos del producto -> {datos_producto} ")
                
                _logger.info(f"Prompt GPT --> {datos_producto_limpio}")


                admin_user_id = request.env.ref('base.user_admin').id
                # Cambia temporalmente el entorno al usuario administrador
                request.env = request.env(user=admin_user_id)



                ##LOGICA GPT
                config = request.env['vex.gpt.config'].get_gpt_config()
                enable_gpt_responder = True
                chatgpt_key = config.get('chatgpt_key', '')
                client_gpt = OpenAI(api_key = chatgpt_key)

                existing_entry = request.env['vex.prompt.history'].sudo().search([('question_id', '=', meli_question_id)], limit=1)
                if existing_entry:
                        _logger.info(f"Ya existe un registro con question_id {meli_question_id}. No se creará uno nuevo.")
                        return http.Response("OK", status=200, headers={'Content-Type': 'text/plain'})


                if enable_gpt_responder:
                    respuesta_gpt = self.responder_pregunta_producto(original_question,datos_producto_limpio,client_gpt)
                    _logger.info(f"LA IA RESPONDERA CON ESTO ---> {respuesta_gpt}")
                                                            
                    history_entry = request.env['vex.prompt.history'].sudo().create({
                        'item_id': item_id_meli,
                        'question_id': meli_question_id,
                        'question_text': original_question,
                        'instance_id': instance.id,
                        'is_answered': False,  # Inicialmente no respondida
                        'gpt_response': respuesta_gpt,
                    })
                    _logger.info(f"Nuevo registro creado en vex.prompt.history: {history_entry.id}")
                                    

                
                _logger.info("WEBHOOK END-----------")


            
            
                                 
            return http.Response("OK", status=200, headers={'Content-Type': 'text/plain'})


        except Exception as e:
            _logger.exception("Error en el webhook: %s", str(e))
            _logger.info("WEBHOOK END-----------")
            return http.Response("OK", status=200, headers={'Content-Type': 'text/plain'})

    
    def crear_pregunta_meli(self, env, datos_pregunta):
        """
        Crea una entrada en el modelo `vex.meli.questions` con los datos proporcionados.

        Args:
            env: `request.env` actual para acceder al entorno de Odoo.
            datos_pregunta (dict): Diccionario con los datos necesarios para crear la entrada.

        Returns:
            record: Registro creado en el modelo `vex.meli.questions`.
        """
        return env['vex.meli.questions'].create({
            'name': datos_pregunta.get('name', 'Pregunta sin nombre'),
            'meli_created_at': datos_pregunta.get('meli_created_at'),
            'meli_item_id': datos_pregunta.get('meli_item_id'),
            'meli_seller_id': datos_pregunta.get('meli_seller_id'),
            'meli_status': datos_pregunta.get('meli_status', 'open'),
            'meli_text': datos_pregunta.get('meli_text'),
            'meli_id': datos_pregunta.get('meli_id'),
            'meli_deleted_from_listing': datos_pregunta.get('meli_deleted_from_listing', False),
            'meli_hold': datos_pregunta.get('meli_hold', False),
            'meli_answer': datos_pregunta.get('meli_answer'),
            'meli_from_id': datos_pregunta.get('meli_from_id'),
            'meli_from_nickname': datos_pregunta.get('meli_from_nickname'),
            'meli_answered_at': datos_pregunta.get('meli_answered_at'),
            'meli_answered_from_odoo': datos_pregunta.get('meli_answered_from_odoo', False),
            'meli_odoo_answerer': datos_pregunta.get('meli_odoo_answerer', ''),
            'meli_import_type': datos_pregunta.get('meli_import_type', 'automatic'),
        })


    @http.route('/custom/view_pdf_label', type='http', auth='user')
    def view_pdf_label(self, **kwargs):
        # Recupera el PDF codificado en Base64 de ir.config_parameter
        encoded_pdf = request.env['ir.config_parameter'].sudo().get_param('current_shipping_label')
        if not encoded_pdf:
            return request.not_found()

        # Decodifica el PDF
        pdf_binary = base64.b64decode(encoded_pdf)

        # Sirve el PDF
        return request.make_response(
            pdf_binary,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'inline; filename="shipping_label.pdf"'),
            ]
        )


    @http.route('/meli/notificationer', type='http', auth='public', website=True, csrf=False)
    def meli_webhook(self, **kwargs):
        try:
            # Obtener los datos JSON del cuerpo de la solicitud
            body = request.get_json_data()
            _logger.info("WEBHOOK RECIBIDO DEVELOPMENT-----------")
            _logger.info(body)

            # Buscar la instancia relacionada con la aplicación
            instance = request.env['vex.instance'].sudo().search([('user_id', '=', body.get('user_id'))], limit=1)

            if not instance:
                _logger.warning("Instancia no encontrada para user_id: %s", body.get('user_id'))
                _logger.info("WEBHOOK END-----------")
                return http.Response("OK", status=200)


            topic = body.get('topic')
            if topic == 'questions':
                _logger.info("Procesando topic: 'questions'")
                try:
                    self.handle_questions(instance, body)
                except Exception as e:
                    _logger.info("Error al procesar la pregunta: %s", str(e))
            elif topic == 'items':
                _logger.info("Procesando topic: 'items' - Actualizando datos del producto")
                self.update_stock(instance, body)
            elif topic == 'orders_v2':
                _logger.info("Procesando topic: 'orders_v2' - Tema de ordenes")
                self.order_topic(instance, body)
            elif topic == 'messages':
                _logger.info("Procesando topic: 'messages'")
                self.messages_topic(instance, body)
            elif topic == 'claims':                    
                _logger.info("Procesando topic: 'claims'")
                self.claims_topic(instance, body)
            
            else:
                _logger.warning("Topic desconocido: %s", topic)

            _logger.info("WEBHOOK END-----------")
            return http.Response("OK", status=200)

        except Exception as e:
            _logger.exception("Error en el webhook: %s", str(e))
            _logger.info("WEBHOOK END-----------")
            return http.Response("OK", status=200)
        
    def send_message_with_order_link(self, order_id, message):
        _logger.info(f"Enviando mensajes para la orden {order_id}")
        try:                                                
            users = request.env['res.users'].search([('active', '=', True)])
            _logger.info(f"Usuarios activos encontrados: {len(users)}")

            partners = users.mapped('partner_id')
            _logger.info(f"Partners asociados encontrados: {len(partners)}")

            # Envía un mensaje a cada usuario
            for partner in partners:
                request.env['mail.message'].create({
                    'model': 'discuss.channel',
                    'body': message,  # Cuerpo del mensaje con el enlace
                    'message_type': 'comment',  # Tipo de mensaje
                    'subtype_id': request.env.ref('mail.mt_comment').id,  # Subtipo del mensaje
                    'partner_ids': [(4, partner.id)],  # Asocia el mensaje al partner
                    'author_id': request.env.user.partner_id.id,  # Autor del mensaje
                    'res_id': 1,  # ID del canal de discusión
                })
                _logger.info(f"Mensaje enviado a partner {partner.name} (ID: {partner.id} {message})")


        except Exception as e:
            _logger.error(f"Error al enviar mensajes para la orden {order_id}: {str(e)}")

    def messages_topic(self,instance,body):
        _logger.info("Procesando mensajes TODO 12312")
        message_id = body['resource']
        message_meli = self.get_message_details(message_id=message_id,access_token=instance.access_token)

        messages = message_meli.get("messages", [])

        # Inicializar el valor del meli_code
        meli_code = None
        aplication_id = body['application_id']

        # Recorrer los mensajes y buscar 'packs' en 'message_resources'
        for message in messages:
            message_resources = message.get("message_resources", [])
            for resource in message_resources:
                if resource.get("name") == "packs":
                    meli_code = resource.get("id")
                    break
            if meli_code:
                break
        if not meli_code:
            _logger.info("No hay orden id para el mensaje")
            return


        _logger.info(f"Actualizando todos los mensajes de la orden {meli_code}")

        admin_user_id = request.env.ref('base.user_admin').id
        # Cambia temporalmente el entorno al usuario administrador
        request.env = request.env(user=admin_user_id)


        #product = request.env['vex.mediations'].

        instance = request.env['vex.instance'].sudo().search([('app_id', '=', aplication_id)], limit=1)
        acces_token = instance.access_token
        seller_id = instance.user_id
        messages_history = request.env['vex.import.wizard'].sudo().get_messages(order_id=meli_code,access_token=acces_token,seller_id=seller_id,debug=True)
        _logger.info(messages_history)
        #message_procesed = self.procesar_mensajes(messages_history)
        message_procesed = request.env['vex.import.wizard'].sudo().procesar_mensajes(messages_history)
        for i in message_procesed:
            _logger.info(i)
        _logger.info("Guardando mensajes")
        crear = request.env['vex.mediations'].sudo().create_messages_for_order(meli_code,message_procesed)
        _logger.info(crear)    

    def claims_topic(self,instance,body):
        resource = body['resource']
        claim_id = resource.split('/')[-1]
        
        claim_info = self.get_claim_details(claim_id=claim_id,access_token=instance.access_token)
        _logger.info(f"Claim info: {claim_info}")

        status = claim_info['status']
        order_meli_id = claim_info['resource_id']

            
        admin_user_id = request.env.ref('base.user_admin').id
        request.env = request.env(user=admin_user_id)  

        self.process_and_store_claim(claim_info=claim_info,instanceid = instance.id)
        order = request.env['sale.order'].sudo().search([('meli_code', '=', int(order_meli_id))], limit=1)

        order = request.env['sale.order'].sudo().search([('meli_code', '=', int(order_meli_id))], limit=1)
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        order_url = f"{base_url}/web#id={order.id}&model=sale.order&view_type=form"

        if status == "opened":

            _logger.info("Logic for when this order , claim is opened")

            

            if order:
                get_partiall_refund_if_exists = request.env['vex.soluciones.mercadolibre.claim'].sudo().get_partial_refund_offers(claim_id=claim_id,access_token=instance.access_token)
                mercadolibre_claim = request.env['vex.soluciones.mercadolibre.claim'].sudo().search([('claim_id', '=', claim_id)], limit=1)
                if mercadolibre_claim and get_partiall_refund_if_exists:
                    mercadolibre_claim.sudo().write({'partial_reffund_options': str(get_partiall_refund_if_exists)})

                if order.in_mediation:
                    _logger.info("The order is already in mediation")
                else:
                    order.sudo().write({'in_mediation': True})
                    _logger.info(f"Status of the mediation in order {order_meli_id} changed to True")
                    self.create_claim_started_message(order_meli_id)

                    
                    message_body = f"Se ha iniciado una reclamacion para la orden: <a href='{order_url}'>Orden {order.name}</a>"
                
                    self.send_message_with_order_link(order_id=order.id, message=message_body)

                    
                    
            claim_messages = self.get_claim_messages(claim_id=claim_id,access_token=instance.access_token,debug=True)
            procesed_claim_messages = self.proces_claim_messages(claim_messages)

            for i in procesed_claim_messages:
                _logger.info(i)

            self.create_messages_for_claim(meli_order_id=order_meli_id,messages=procesed_claim_messages,marketplace_nick=instance.nick)
            
           # self.update_claim_messages()
        else:            
            _logger.info("Logic for when this order , claim is closed")

            if order.in_mediation:
                order.sudo().write({'in_mediation': False})
                order.sudo().write({'expected_resolution': False})
                order.sudo().write({'mediation_solved': True})
                _logger.info(f"Status of the mediation in order {order_meli_id} changed to False")
                self.create_claim_closed_message(order_meli_id)
                message_body = f"La mediacion ha sido cerrada, la orden ha sido marcada como resuelta: <a href='{order_url}'>Orden {order.name}</a>"
                self.send_message_with_order_link(order.id, message_body)

    def process_and_store_claim(self, claim_info ,instanceid):
        """
        Process a claim dictionary, check if the claim_id exists, and create or update the record.
        :param claim_info: Dictionary containing claim details
        """

        def parse_datetime(date_str):
            """
            Convert ISO 8601 string to Odoo's datetime format.
            """
            try:
                # Parse ISO 8601 format
                return datetime.strptime(date_str.split('.')[0], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                _logger.error("Error parsing datetime: %s", e)
                return None
        # Extract the claim_id from the incoming data
        claim_id = claim_info.get('id')
        if not claim_id:
            _logger.error("Claim data does not contain an 'id'.")
            return

        # Check if the claim already exists in the database
        existing_claim = request.env['vex.soluciones.mercadolibre.claim'].search([('claim_id', '=', claim_id)], limit=1)

        # Extract relevant data
        resource_id = claim_info.get('resource_id')
        status = claim_info.get('status')
        type_ = claim_info.get('type')
        stage = claim_info.get('stage')
        reason_id = claim_info.get('reason_id')
        fulfilled = claim_info.get('fulfilled')
        quantity_type = claim_info.get('quantity_type')
        site_id = claim_info.get('site_id')
        date_created = parse_datetime(claim_info.get('date_created'))
        last_updated = parse_datetime(claim_info.get('last_updated'))   
        resolution = claim_info.get('resolution')

        # Extract players
        players = claim_info.get('players', [])
        complainant = next((p for p in players if p.get('role') == 'complainant'), {})
        respondent = next((p for p in players if p.get('role') == 'respondent'), {})
        complainant_id = complainant.get('user_id')
        respondent_id = respondent.get('user_id')
        available_actions = ', '.join([action.get('action') for action in respondent.get('available_actions', [])])

        # Create or update the claim record
        if existing_claim:
            _logger.info("Updating existing claim with ID: %s", claim_id)
            existing_claim.write({
                'resource_id': resource_id,
                'status': status,
                'type': type_,
                'stage': stage,
                'reason_id': reason_id,
                'fulfilled': fulfilled,
                'quantity_type': quantity_type,
                'complainant_id': complainant_id,
                'respondent_id': respondent_id,
                'site_id': site_id,
                'date_created': date_created,
                'last_updated': last_updated,
                'resolution': resolution,
                'available_actions': available_actions,
                'instance_id': instanceid,
            })
        else:
            _logger.info("Creating new claim with ID: %s", claim_id)
            request.env['vex.soluciones.mercadolibre.claim'].create({
                'claim_id': claim_id,
                'resource_id': resource_id,
                'status': status,
                'type': type_,
                'stage': stage,
                'reason_id': reason_id,
                'fulfilled': fulfilled,
                'quantity_type': quantity_type,
                'complainant_id': complainant_id,
                'respondent_id': respondent_id,
                'site_id': site_id,
                'date_created': date_created,
                'last_updated': last_updated,
                'resolution': resolution,
                'available_actions': available_actions,
                'instance_id': instanceid,
            })   

        #update sale order status
        #Aqui se gestiona la intervencion de ML
        order = request.env['sale.order'].search([('meli_code', '=', resource_id)], limit=1)
        if order:
            if available_actions == 'send_message_to_mediator' and status == 'opened':
                order.sudo().write({'in_mediation': True})
                order.sudo().write({'waiting_ml_intervention': True}) # Si la orden solo puedes enviar mensajes significa que esta en espera de intervencion de ML
                _logger.info(f"Status of the mediation in order {resource_id} changed to True")
            if status == 'closed':
                order.sudo().write({'in_mediation': False})
                order.sudo().write({'expected_resolution': False})
                order.sudo().write({'mediation_solved': True})
                _logger.info(f"Status of the mediation in order {resource_id} changed to False")
                order.sudo().write({'waiting_ml_intervention': False})
            

        

    def get_claim_details(self,claim_id: str, access_token: str):
        """
        Consulta los detalles de un mensaje en Mercado Libre por su ID.
        
        :param message_id: ID del mensaje a consultar.
        :param access_token: Token de acceso a la API de Mercado Libre.
        :return: Información del mensaje en formato JSON.
        """
        
        # Construir la URL de la solicitud
        url = f"{MERCADO_LIBRE_URL}/post-purchase/v1/claims/{claim_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        try:
            # Log de la solicitud
            _logger.info(f"URL de la solicitud: {url}")
            _logger.info(f"Headers de la solicitud: {headers}")

            # Hacer la solicitud GET
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Eleva una excepción si el código de estado no es 200

            # Log de la respuesta exitosa
            _logger.info(f"Respuesta exitosa. Código de estado: {response.status_code}")
            _logger.info(f"Contenido de la respuesta: {response.text}")

            # Retornar los datos del mensaje
            return response.json()

        except requests.RequestException as e:
            _logger.error(f"Error al consultar el mensaje: {str(e)}")
            if response:
                _logger.error(f"Respuesta de la API: {response.status_code}")
                _logger.error(f"Contenido de la respuesta: {response.text}")
            return None
        
    def get_claim_messages(self, claim_id: str, access_token: str, debug: bool = False):
        """
        Fetches all messages associated with a given claim ID from Mercado Libre's API.

        :param claim_id: ID of the claim in Mercado Libre.
        :param access_token: Mercado Libre access token.
        :param debug: If True, enables detailed logging for debugging purposes.
        :return: List of all messages or None if an error occurs.
        """
        if debug:
            _logger.info(f"Starting to fetch messages for claim_id: {claim_id}")
        
        url = f"https://api.mercadolibre.com/post-purchase/v1/claims/{claim_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        all_messages = []
        offset = 0
        limit = 50  # Default limit for pagination

        try:
            while True:
                paginated_url = f"{url}?offset={offset}&limit={limit}"
                if debug:
                    _logger.info(f"Requesting URL: {paginated_url}")
                    _logger.info(f"Request headers: {headers}")
                
                response = requests.get(paginated_url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                if debug:
                    _logger.info(f"Response status code: {response.status_code}")
                    _logger.info(f"Response content: {response.text}")
                
                # Append fetched messages to the list
                messages = data if isinstance(data, list) else []
                all_messages.extend(messages)
                
                # Check if there are more messages to fetch
                if len(messages) < limit:
                    break
                
                offset += limit
            
            if debug:
                _logger.info(f"Total messages retrieved: {len(all_messages)}")
            
            return all_messages
        
        except requests.exceptions.RequestException as e:
            if debug:
                _logger.error(f"Error while fetching messages: {e}")
            return None

    def proces_claim_messages(self, mensajes):
        """
        Processes a list of messages to extract relevant information and avoid duplicates.

        Args:
            mensajes (list): List of original messages.

        Returns:
            list: List of processed messages with key data.
        """
        mensajes_procesados = {}

        for mensaje in mensajes:
            # Extract relevant fields
            message_text = mensaje.get('message')
            sender_role = mensaje.get('sender_role')
            receiver_role = mensaje.get('receiver_role')
            date_created = mensaje.get('date_created')
            attachments = mensaje.get('attachments', [])
            
            # Use a combination of date_created and message_text as a unique key
            clave_unica = f"{date_created}_{message_text}"

            # Skip if this message already exists
            if clave_unica in mensajes_procesados:
                continue

            # Store the processed message
            mensajes_procesados[clave_unica] = {
                'message': message_text,
                'sender_role': sender_role,
                'receiver_role': receiver_role,
                'date_created': date_created,
                'attachments': attachments
            }

        # Return the unique values as a list
        return list(mensajes_procesados.values())
    

    def create_claim_started_message(self, meli_order_id):
        """
        Creates a single message from the client for the specified order indicating that a claim has started.

        :param meli_order_id: The ID of the order where the message will be displayed.
        :return: The created message record.
        """
        order = request.env['sale.order'].search([('meli_code', '=', meli_order_id)], limit=1)
        if not order.exists():
            raise ValueError(f"No se encontró la orden con ID {meli_order_id}")

        # Current timestamp in UTC
        current_datetime = datetime.now(timezone.utc).replace(tzinfo=None)


        # Prepare message details
        message_text = "--------CLAIM STARTED FROM THE CLIENT---------"
        author = order.partner_id  

        if not author:
            _logger.warning(f"No se encontró un cliente asociado a la orden {meli_order_id}. Asignando autor genérico.")
            author = request.env['res.partner'].create({'name': 'Autor desconocido'})

        # Create the message in Odoo
        created_message = request.env['mail.message'].create({
            'res_id': order.id,
            'model': 'sale.order',
            'body': message_text,
            'author_id': author.id,
            'message_type': 'comment',
            'date': current_datetime,
            'from_marketplace': True
        })

        _logger.info(f"Mensaje creado: '{message_text}' para la orden {meli_order_id}.")

        return created_message
    
    def create_claim_closed_message(self, meli_order_id):
        """
        Creates a single message from the client for the specified order indicating that a claim has started.

        :param meli_order_id: The ID of the order where the message will be displayed.
        :return: The created message record.
        """
        order = request.env['sale.order'].search([('meli_code', '=', meli_order_id)], limit=1)
        if not order.exists():
            raise ValueError(f"No se encontró la orden con ID {meli_order_id}")

        # Current timestamp in UTC
        current_datetime = datetime.now(timezone.utc).replace(tzinfo=None)


        # Prepare message details
        message_text = "--------CLAIM CLOSED---------"
        author = order.partner_id  

        if not author:
            _logger.warning(f"No se encontró un cliente asociado a la orden {meli_order_id}. Asignando autor genérico.")
            author = request.env['res.partner'].create({'name': 'Autor desconocido'})

        # Create the message in Odoo
        created_message = request.env['mail.message'].create({
            'res_id': order.id,
            'model': 'sale.order',
            'body': message_text,
            'author_id': author.id,
            'message_type': 'comment',
            'date': current_datetime,
            'from_marketplace': True
        })

        _logger.info(f"Mensaje creado: '{message_text}' para la orden {meli_order_id}.")

        return created_message



    def create_messages_for_claim(self, meli_order_id, messages,marketplace_nick):
        """
        Creates multiple messages associated with an order, avoiding duplicates.

        :param meli_order_id: The ID of the order where the messages will be displayed.
        :param messages: List of messages to create, each in format:
                        {'message': 'text', 'date_created': '2025-01-02T15:44:08.000-04:00',
                        'sender_role': 'complainant', 'receiver_role': 'respondent', 'attachments': []}
        :return: List of created messages or log of existing messages.
        """
        order = request.env['sale.order'].search([('meli_code', '=', meli_order_id)], limit=1)
        if not order.exists():
            raise ValueError(f"No se encontró la orden con ID {meli_order_id}")

        created_messages = []

        for message_data in reversed(messages):  # Reverse to create messages in chronological order
            message_text = message_data.get('message')
            date_created = message_data.get('date_created')

            # Transformar 'date_created' al horario local
            try:
                # Parsear la fecha con zona horaria incluida
                utc_date = datetime.fromisoformat(date_created.replace('Z', '+00:00'))

                # Comprobar si ya tiene tzinfo
                if utc_date.tzinfo is not None:
                    # Convertir directamente a la zona horaria local si ya tiene tzinfo
                    local_timezone = pytz.timezone('America/Mexico_City')  # Ajusta según tu zona horaria local
                    fecha_envio = utc_date.astimezone(local_timezone).replace(tzinfo=None)
                    _logger.info(f"Fecha convertida a la zona horaria local: {fecha_envio}")
                else:
                    # Localizar y luego convertir si no tiene tzinfo
                    original_timezone = pytz.timezone('America/Caracas')  # Cambia según sea necesario
                    localized_date = original_timezone.localize(utc_date)
                    local_timezone = pytz.timezone('America/Mexico_City')  # Cambia según sea necesario
                    fecha_envio = localized_date.astimezone(local_timezone).replace(tzinfo=None)
                    _logger.info(f"Fecha convertida a la zona horaria local: {fecha_envio}")
            except ValueError as e:
                _logger.error(f"Formato de fecha inválido para el mensaje: {date_created}. Error: {e}")
                continue

            # Metodo antiguo que no tomaba en cuenta la tolerancia de timezone
            # try:
            #     fecha_envio = datetime.fromisoformat(date_created.replace('Z', '+00:00')).replace(tzinfo=None)
            # except ValueError:
            #     _logger.error(f"Formato de fecha inválido para el mensaje: {date_created}")
            #     continue

            tolerance = timedelta(minutes=5)
            fecha_inicio = fecha_envio - tolerance
            fecha_fin = fecha_envio + tolerance

            existing_message = request.env['mail.message'].search([
                ('res_id', '=', order.id),
                ('model', '=', 'sale.order'),
                ('body', '=', message_text),
                ('date', '>=', fecha_inicio),
                ('date', '<=', fecha_fin),
            ], limit=1)
            if existing_message:
                _logger.info(f"El mensaje '{message_text}' con fecha '{date_created}' ya existe para la orden {meli_order_id}.  Saltando...")
                continue

            # Determine the author based on sender_role
            sender_role = message_data.get('sender_role')
            if sender_role == 'complainant':
                author = order.partner_id  # Use the customer/buyer from the order
            elif sender_role == 'respondent':
                #Significa que el mensaje viene de la tienda asi que usaremos su Nick para usarlo como usuario
                author = request.env['res.partner'].search([('name', '=', marketplace_nick)], limit=1)
                if not author:
                    _logger.warning(f"Se encontro que tienda manda el mensaje, pero no tiene su usuario... creando '{marketplace_nick}'. Creando...")
                    author = request.env['res.partner'].create({'name': marketplace_nick})

            # Create the message in Odoo
            created_message = request.env['mail.message'].create({
                'res_id': order.id,
                'model': 'sale.order',
                'body': message_text,
                'author_id': author.id,
                'message_type': 'comment',
                'date': fecha_envio,
                'from_marketplace': True
            })

            created_messages.append(created_message)
            _logger.info(f"Mensaje creado: '{message_text}' para la orden {meli_order_id}. con fecha {fecha_envio}")

        if not created_messages:
            _logger.info(f"No se crearon mensajes nuevos para la orden {meli_order_id}.")
        else:
            _logger.info(f"Se crearon {len(created_messages)} mensajes nuevos para la orden {meli_order_id}.")

        return created_messages


    #@api.model
    def create_message_for_order(self, message_json):
        """
        Crea un mensaje asociado a una orden basada en un JSON proporcionado.
        :param message_json: JSON con los datos del mensaje
        """
        # Extraer los datos necesarios del JSON
        meli_code = None
        for resource in message_json.get('message_resources', []):
            if resource.get('name') == 'packs':  # Verifica que sea el meli_code
                meli_code = resource.get('id')
                break

        if not meli_code:
            raise ValueError("El mensaje no contiene un 'meli_code' válido en los 'message_resources'.")

        # Verificar si la orden existe
        order = self.env['sale.order'].search([('meli_code', '=', meli_code)], limit=1)
        if not order:
            raise ValueError(f"No se encontró la orden con el meli_code {meli_code}.")

        # Extraer información del mensaje
        message_id = message_json.get('id')
        message_text = message_json.get('text')
        sender_id = message_json.get('from', {}).get('user_id')
        message_date = message_json.get('message_date', {}).get('created')

        if not (message_id and message_text and sender_id and message_date):
            raise ValueError("El JSON proporcionado no contiene todos los datos necesarios.")

        # Convertir 'message_date' a datetime
        fecha_envio = datetime.fromisoformat(message_date.replace('Z', '+00:00')).replace(tzinfo=None)

        # Verificar si el mensaje ya existe
        existing_message = self.env['mail.message'].search([('unique_message_id', '=', message_id)], limit=1)
        if existing_message:
            _logger.info(f"El mensaje con ID único '{message_id}' ya existe para la orden {meli_code}.")
            return existing_message

        # Buscar o crear el autor (remitente)
        author = self.env['res.partner']

        tienda =  self.env['vex.instance'].search([('user_id', '=', sender_id)], limit=1)
        if tienda: #Significa que el mensaje viene de la tienda asi que usaremos su Nick para usarlo como usuario
                nick = tienda.nick
                author = self.env['res.partner'].search([('name', '=', nick)], limit=1)
                if not author:
                    _logger.warning(f"Se encontro que tienda manda el mensaje, pero no tiene su usuario... creando '{nick}'. Creando...")
                    author = self.env['res.partner'].create({'name': nick})
        else:
            #Aqui buscar el res.partner del sale order, el commprador
            author = order.partner_id
            if not author:
                _logger.warning(f"No se encontró un autor para el mensaje, y la orden no tiene un comprador asociado. Asignando autor genérico.")
                author = self.env['res.partner'].create({'name': 'Autor desconocido'})


        created_message = self.env['mail.message'].create({
            'res_id': order.id,  
            'model': 'sale.order',  
            'body': message_text,  
            'author_id': author.id,  
            'message_type': 'comment', 
            'date': fecha_envio,  
            'unique_message_id': message_id,  
            'from_marketplace': True
        })

        _logger.info(f"Mensaje creado con ID único '{message_id}' para la orden {meli_code}.")
        return created_message
    

    # ------------------------- RECLAMOS -------------------------

    def get_reclamo_details(self, reclamo_id: str, access_token: str):
        """Obtiene detalles de un reclamo específico."""
        _logger.info(f"[START] Consultando detalles del reclamo con ID {reclamo_id}")
        url = f"{MERCADO_LIBRE_URL}/claims/{reclamo_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        try:
            response = requests.get(url, headers=headers)
            _logger.info(f"[SUCCESS] Respuesta recibida. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al consultar el reclamo: {str(e)}")
            return None

    def create_reclamo(self, order_id: str, reason: str, access_token: str):
        """Crea un nuevo reclamo."""
        _logger.info(f"[START] Creando reclamo para la orden {order_id}")
        url = f"{MERCADO_LIBRE_URL}/claims"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "order_id": order_id,
            "reason": reason
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        _logger.debug(f"[DATA] Payload: {payload}")
        try:
            response = requests.post(url, json=payload, headers=headers)
            _logger.info(f"[SUCCESS] Reclamo creado. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al crear el reclamo: {str(e)}")
            return None

    def resolve_reclamo(self, reclamo_id: str, resolution: str, access_token: str):
        """Resuelve un reclamo."""
        _logger.info(f"[START] Resolviendo reclamo con ID {reclamo_id}")
        url = f"{MERCADO_LIBRE_URL}/claims/{reclamo_id}/resolution"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "resolution": resolution
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        _logger.debug(f"[DATA] Payload: {payload}")
        try:
            response = requests.put(url, json=payload, headers=headers)
            _logger.info(f"[SUCCESS] Reclamo resuelto. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al resolver el reclamo: {str(e)}")
            return None

    def add_evidence_to_reclamo(self, reclamo_id: str, evidence: dict, access_token: str):
        """Añade evidencia a un reclamo."""
        _logger.info(f"[START] Añadiendo evidencia al reclamo con ID {reclamo_id}")
        url = f"{MERCADO_LIBRE_URL}/claims/{reclamo_id}/evidence"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        _logger.debug(f"[DATA] Payload (evidencia): {evidence}")
        try:
            response = requests.post(url, json=evidence, headers=headers)
            _logger.info(f"[SUCCESS] Evidencia añadida. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al añadir evidencia: {str(e)}")
            return None

    def get_reclamo_messages(self, reclamo_id: str, access_token: str):
        """Obtiene mensajes relacionados a un reclamo."""
        _logger.info(f"[START] Consultando mensajes del reclamo con ID {reclamo_id}")
        url = f"{MERCADO_LIBRE_URL}/claims/{reclamo_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        try:
            response = requests.get(url, headers=headers)
            _logger.info(f"[SUCCESS] Mensajes recuperados. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al obtener mensajes: {str(e)}")
            return None

    def send_reclamo_message(self, reclamo_id: str, message: str, access_token: str):
        """Envía un mensaje relacionado a un reclamo."""
        _logger.info(f"[START] Enviando mensaje al reclamo con ID {reclamo_id}")
        url = f"{MERCADO_LIBRE_URL}/claims/{reclamo_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "message": message
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        _logger.debug(f"[DATA] Payload: {payload}")
        try:
            response = requests.post(url, json=payload, headers=headers)
            _logger.info(f"[SUCCESS] Mensaje enviado. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al enviar mensaje al reclamo: {str(e)}")
            return None

    # ------------------------- MENSAJERÍA -------------------------

    def get_conversation_details(self, conversation_id: str, access_token: str):
        """Obtiene los detalles de una conversación por su ID."""
        _logger.info(f"[START] Consultando detalles de la conversación con ID {conversation_id}")
        url = f"{MERCADO_LIBRE_URL}/messages/{conversation_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        try:
            response = requests.get(url, headers=headers)
            _logger.info(f"[SUCCESS] Respuesta recibida. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al consultar detalles de la conversación: {str(e)}")
            return None

    def send_message(self, user_id: str, message: str, access_token: str):
        """Envía un mensaje a un usuario específico."""
        _logger.info(f"[START] Enviando mensaje al usuario con ID {user_id}")
        url = f"{MERCADO_LIBRE_URL}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "to": [{"user_id": user_id}],
            "text": {"plain": message}
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        _logger.debug(f"[DATA] Payload: {payload}")
        try:
            response = requests.post(url, json=payload, headers=headers)
            _logger.info(f"[SUCCESS] Mensaje enviado. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al enviar mensaje: {str(e)}")
            return None

    def send_message_with_image(self, user_id: str, message: str, image_url: str, access_token: str):
        """Envía un mensaje con una imagen a un usuario."""
        _logger.info(f"[START] Enviando mensaje con imagen al usuario con ID {user_id}")
        url = f"{MERCADO_LIBRE_URL}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "to": [{"user_id": user_id}],
            "text": {"plain": message},
            "attachments": [{"source": {"url": image_url}}]
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        _logger.debug(f"[DATA] Payload: {payload}")
        try:
            response = requests.post(url, json=payload, headers=headers)
            _logger.info(f"[SUCCESS] Mensaje con imagen enviado. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al enviar mensaje con imagen: {str(e)}")
            return None

    def upload_image(self, image_path: str, access_token: str):
        """Sube una imagen para usarla en mensajería."""
        _logger.info(f"[START] Subiendo imagen desde la ruta {image_path}")
        url = f"{MERCADO_LIBRE_URL}/pictures"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        try:
            with open(image_path, "rb") as image_file:
                files = {"file": image_file}
                response = requests.post(url, files=files, headers=headers)
            _logger.info(f"[SUCCESS] Imagen subida. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al subir imagen: {str(e)}")
            return None

    def get_conversation_messages(self, conversation_id: str, access_token: str):
        """Obtiene todos los mensajes de una conversación."""
        _logger.info(f"[START] Consultando mensajes de la conversación con ID {conversation_id}")
        url = f"{MERCADO_LIBRE_URL}/messages/{conversation_id}/history"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        try:
            response = requests.get(url, headers=headers)
            _logger.info(f"[SUCCESS] Mensajes recuperados. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al consultar mensajes: {str(e)}")
            return None

    def send_bulk_messages(self, user_ids: list, message: str, access_token: str):
        """Envía mensajes a múltiples usuarios."""
        _logger.info(f"[START] Enviando mensajes a múltiples usuarios")
        url = f"{MERCADO_LIBRE_URL}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        recipients = [{"user_id": user_id} for user_id in user_ids]
        payload = {
            "to": recipients,
            "text": {"plain": message}
        }
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        _logger.debug(f"[DATA] Payload: {payload}")
        try:
            response = requests.post(url, json=payload, headers=headers)
            _logger.info(f"[SUCCESS] Mensajes enviados. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al enviar mensajes: {str(e)}")
            return None

    def get_message_details(self,message_id: str, access_token: str):
        """
        Consulta los detalles de un mensaje en Mercado Libre por su ID.
        
        :param message_id: ID del mensaje a consultar.
        :param access_token: Token de acceso a la API de Mercado Libre.
        :return: Información del mensaje en formato JSON.
        """
        _logger.info(f"Iniciando consulta del mensaje con ID {message_id}")

        # Construir la URL de la solicitud
        url = f"{MERCADO_LIBRE_URL}/messages/{message_id}?tag=post_sale"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        try:
            # Log de la solicitud
            _logger.info(f"URL de la solicitud: {url}")
            _logger.info(f"Headers de la solicitud: {headers}")

            # Hacer la solicitud GET
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Eleva una excepción si el código de estado no es 200

            # Log de la respuesta exitosa
            _logger.info(f"Respuesta exitosa. Código de estado: {response.status_code}")
            _logger.info(f"Contenido de la respuesta: {response.text}")

            # Retornar los datos del mensaje
            return response.json()

        except requests.RequestException as e:
            _logger.error(f"Error al consultar el mensaje: {str(e)}")
            if response:
                _logger.error(f"Respuesta de la API: {response.status_code}")
                _logger.error(f"Contenido de la respuesta: {response.text}")
            return None



    def order_topic(self,instance, body):
        _logger.info(f"instancia : {instance.app_id} y el body {body}")
        meli_order_id = body['resource'].split('/')[-1]

        admin_user_id = request.env.ref('base.user_admin').id
        # Cambia temporalmente el entorno al usuario administrador
        request.env = request.env(user=admin_user_id)
        

        order_exists = request.env['sale.order'].sudo().search([('meli_code', '=', meli_order_id)], limit=1)

        if order_exists:
            buyer_id = order_exists.partner_id.meli_user_id  
            _logger.info(f"La orden {meli_order_id} ya existe, actualizando estado de orden...{buyer_id}")


           
            estado_anterior = order_exists.order_status
            _logger.info(f"El estado anterior de la orden es {estado_anterior}")
            import_line_temp = request.env['vex.import_line'].create({
                'description': f"{meli_order_id}",
                'instance_id': instance.id,  # Relacionar con la instancia real
            })
            vex_sycnro = request.env['vex.synchro']
            vex_sycnro.sync_order(import_line_temp)
            order_exists = request.env['sale.order'].sudo().search([('meli_code', '=', meli_order_id)], limit=1)

            estado_actualizado = order_exists.order_status
            _logger.info(f"El estado actualizado de la orden es {estado_anterior}")    

            
            if estado_anterior == "Pending" and estado_actualizado == "Completada": #Este flujo solo puede causar una vez por orden por lo que no hay que asegurarnos que la no factura se halla enviado anteriormente
                _logger.info("Detectado cambio de la orden de Pendiente a Completada")
                _logger.info("Enviando factura")  

                order_invoice = request.env['sale.order'].sudo().search([('meli_code', '=', meli_order_id)], limit=1)
                invoice = order_invoice.invoice_ids and order_invoice.invoice_ids[0]

                link_factura = "http://localhost:8069/my/invoices/20?access_token=092a83ba-eb9d-476d-a9be-907080471516"
                texto_usuario = "En caso de necesitar su factira , por favor haga click aqui"

                if invoice:
                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')  # URL base del sistema
                    access_token = invoice.access_token  # Token de acceso público

                    # Generar manualmente el token si no existe
                    if not invoice.access_token:
                        # Generar un token único manualmente
                        token = uuid.uuid4().hex  # Crea un token único basado en UUID
                        invoice.sudo().write({'access_token': token})

                    link_factura = f"{base_url}/my/invoices/{invoice.id}?access_token={invoice.access_token}"
                    _logger.info(f"Enlace para compartir la factura: {link_factura}")

                    

                    mensaje = f'{texto_usuario}: <a href="{link_factura}">Ver Factura</a>'

                    self.send_user_invoice(meli_order_id,mensaje,instance.access_token,instance.user_id,buyer_id )
                
                else:
                    _logger.info("No se encontro factura para la orden")
                
                
                
                
        else:
            _logger.info(f"La orden {meli_order_id} no existe.. creando")
            import_line_temp = request.env['vex.import_line'].new({                       
                        'description': f"{meli_order_id}",  
                        'instance_id': request.env['vex.instance'].new({
                        'access_token': instance.access_token  # Copiar el access_token de la instancia original
                         })})
            
            vex_sycnro = request.env['vex.synchro']
            vex_sycnro.sync_order(import_line_temp)


    def send_user_invoice(self ,order_id:str ,response:str,accessToken,seller_id:int,buyer_id):
       
        _logger.info(f"Iniciando envio factura de la orden {order_id}")

        url = f"{MERCADO_LIBRE_URL}/messages/packs/{order_id}/sellers/{seller_id}?tag=post_sale"
        headers = {
            "Authorization": f"Bearer {accessToken}",
            "Content-Type": "application/json"
        }

        try:
            body = {
                "from": {
                    "user_id": seller_id  
                },
                "to": {
                    "user_id": buyer_id  
                },
                "text": response  # El mensaje que queremos enviar
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

        except requests.RequestException as e:
            _logger.info(f"Error al responder la pregunta: {str(e)}")
            # Agrega logging para verificar la respuesta
            _logger.info(f"Respuesta de la API: {answered.status_code}")
            _logger.info(f"Contenido de la respuesta: {answered.text}")
            
        _logger.info(f"Factura a la orden {order_id} enviada correctamente.")

    
    def send_pos_sale_message(self ,order_id:str ,response:str,accessToken,seller_id:int,buyer_id):
       
        _logger.info(f"Iniciando envio mensaje {order_id}")

        url = f"{MERCADO_LIBRE_URL}/messages/packs/{order_id}/sellers/{seller_id}?tag=post_sale"
        headers = {
            "Authorization": f"Bearer {accessToken}",
            "Content-Type": "application/json"
        }

        try:
            body = {
                "from": {
                    "user_id": seller_id  
                },
                "to": {
                    "user_id": buyer_id  
                },
                "text": response  # El mensaje que queremos enviar
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

        except requests.RequestException as e:
            _logger.info(f"Error al responder la pregunta: {str(e)}")
            # Agrega logging para verificar la respuesta
            _logger.info(f"Respuesta de la API: {answered.status_code}")
            _logger.info(f"Contenido de la respuesta: {answered.text}")
            
        _logger.info(f"Factura a la orden {order_id} enviada correctamente.")


    

    
    def clean_text(self, text):
        # Convertir a minúsculas
        text = text.lower()
        # Eliminar caracteres especiales y espacios
        text = re.sub(r'[^a-z0-9]', '', text)
        return text
    
    
    def parse_iso_datetime(self, iso_string):
        """Convierte el formato ISO 8601 a un formato compatible con Odoo."""
        try:
            return datetime.strptime(iso_string, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            # Si la microsegundos están ausentes en la cadena
            return datetime.strptime(iso_string, '%Y-%m-%dT%H:%M:%SZ')
    
 
        
    def make_request(self, instance, resource):
        """Realiza una solicitud GET a la API de Mercado Libre usando el resource"""
        API_URL = f"https://api.mercadolibre.com{resource}"
        
        headers = {
            'Authorization': f"Bearer {instance.meli_access_token}"
        }
        _logger.info(f"Making request to: {API_URL} , {headers}", 'info')
        
        try:
            response = requests.get(API_URL,headers=headers)
            response.raise_for_status()  # Verifica si hubo algún error
            _logger.info(f"Request successful: {API_URL}", 'info')
            return response.json()  # Devolver el contenido como JSON
        except requests.exceptions.HTTPError as http_err:
            _logger.info(f"HTTP error occurred: {http_err}", 'error')
        except Exception as err:
            _logger.info(f"Other error occurred: {err}", 'error')

        return None

    # Procesamiento de cada topic con solicitud al resource
    def process_items_prices(self, instance, body):
        """Procesa la solicitud de 'items_prices'."""
        _logger.info(f"Processing items_prices: {body['resource']}")
        response = self.make_request(instance, body['resource'])
        if response:
            # Procesar la respuesta obtenida de la API de Mercado Libre
            _logger.info(f"Response data: {response}")

            product_id = response.get('id')
            instance.update_item_by_sku(product_id) # FALTA OPTIMIZAR ONE REQUEST

            prices = response.get('prices', [])

            # Iterar sobre las diferentes entradas de precios
            for price_data in prices:
                price_amount = price_data.get('amount')
                price_type = price_data.get('type')
                currency_id = price_data.get('currency_id')

                # Registrar el cambio de precio si es necesario
                # product = self.env['product.template'].sudo().search([('default_code', '=', product_id)], limit=1)
                # if product:
                #     pass
                    # product.update_price(price_amount) PRONTO

    def process_items(self, instance, body):
        """Procesa la solicitud de 'items'."""
        _logger.info(f"Processing items: {body['resource']}")
        response = self.make_request(instance, body['resource'])
        if response:
            # Aquí procesas la respuesta obtenida de la API de Mercado Libre
            _logger.info(f"Response data: {response}")
            product_id = response.get('id')
            instance.update_item_by_sku(product_id) # FALTA OPTIMIZAR ONE REQUEST

    def process_orders(self, instance, body):
        """Procesa la solicitud de 'orders'."""
        _logger.info(f"Processing orders: {body['resource']}")
        response = self.make_request(instance, body['resource'])
        if response:
            # Aquí procesas la respuesta obtenida de la API de Mercado Libre
            _logger.info(f"Response data: {response}")

    def process_orders_v2(self, instance, body):
        """Procesa la solicitud de 'orders_v2'."""
        _logger.info(f"Processing orders_v2: {body['resource']}")
        response = self.make_request(instance, body['resource'])
        if response:
            # Aquí procesas la respuesta obtenida de la API de Mercado Libre
            _logger.info(f"Response data: {response}")

    def process_orders_deleted(self, instance, body):
        """Procesa la solicitud de 'orders_deleted'."""
        _logger.info(f"Processing orders_deleted: {body['resource']}")
        response = self.make_request(instance, body['resource'])
        if response:
            # Aquí procesas la respuesta obtenida de la API de Mercado Libre
            _logger.info(f"Response data: {response}")

    def process_user_products(self, instance, body):
        """Procesa la solicitud de 'user-products'."""
        _logger.info(f"Processing user-products: {body['resource']}")
        response = self.make_request(instance, body['resource'])
        if response:
            # Aquí procesas la respuesta obtenida de la API de Mercado Libre
            _logger.info(f"Response data: {response}")
            
    def process_products_families(self, instance, body):
        """Procesa la solicitud de 'questions'."""
        _logger.info(f"Processing questions: {body['resource']}")
        response = self.make_request(instance, body['resource'])
        if response:
            # Procesar la respuesta obtenida de la API de Mercado Libre
            _logger.info(f"Response data: {response}")

            user_products_ids = response.get('user_products_ids', [])
            family_id = response.get('family_id')
            site_id = response.get('site_id')
            user_id = response.get('user_id')
            
            for product_id in user_products_ids:
                _logger.info(f"Processing product: {product_id}")

        else:
            # Si no hay respuesta o la respuesta es vacía
            _logger.info("No data returned from the API for products families", 'warning')
            
    def process_questions(self, instance, body):
        """Procesa la solicitud de 'questions'."""
        _logger.info(f"Processing questions: {body['resource']}")
        response = self.make_request(instance, body['resource'])
        if response:
            # Aquí procesas la respuesta obtenida de la API de Mercado Libre
            _logger.info(f"Response data: {response}")

    def process_stock_locations(self, instance, body):
        """Procesa la solicitud de 'stock-locations'."""
        _logger.info(f"Processing stock-locations: {body['resource']}")
        response = self.make_request(instance, body['resource'])
        if response:
            # Procesar la respuesta obtenida de la API de Mercado Libre
            _logger.info(f"Response data: {response}")
            
            user_id = response.get('user_id')
            if user_id != instance.perfil_id:
                _logger.info(f"Error: el perfil del webhook no coincide con la instancia User_id:{user_id} - Instance:{instance.perfil_id} .", 'error')
                return  # Detener el procesamiento si no coinciden
            
            user_product_id = response.get('id') 
            locations = response.get('locations', [])
            product_release_date = response.get('product_release_date', None)

            # Iterar sobre las ubicaciones y registrar la cantidad disponible
            for location in locations:
                location_type = location.get('type')
                quantity = location.get('quantity', 0)
                _logger.info(f"Location Type: {location_type}, Quantity: {quantity}")
            # Hacer la solicitud paginada
            # Hacer la solicitud paginada y obtener los IDs de los items y errores
            item_ids, errors = self.get_items_by_user_product(instance, user_id, user_product_id)
            
            if item_ids:
                _logger.info(f"Successfully retrieved item IDs: {item_ids}")
                # Iterar sobre cada item_id y ejecutar una función para procesar cada uno
                for item_id in item_ids:
                    instance.update_item_by_sku(item_id)  # Ejecutar la función para cada item
                    
            if errors:
                _logger.info(f"Errors occurred while fetching items: {errors}")

        else:
            # Si no hay respuesta o la respuesta es vacía
            _logger.info("No data returned from the API for stock-locations", 'warning')
            
    # UTILS
    def get_items_by_user_product(self, instance, user_id, user_product_id):
        """Realiza una solicitud paginada a la API de Mercado Libre para obtener los items de un usuario basado en user_product_id."""
        
        # Inicialización de variables para paginación
        url = f"https://api.mercadolibre.com/users/{user_id}/items/search?user_product_id={user_product_id}"
        headers = {
            'Authorization': f'Bearer {instance.meli_access_token}'
        }
        limit = 50  # Límite de resultados por página
        offset = 0  # Comienza en la primera página
        total = 1  # Número inicial de elementos, se actualizará con la primera respuesta
        
        all_item_ids = []  # Lista para almacenar todos los IDs de los items
        errors = []  # Lista para almacenar los errores ocurridos durante la paginación
        
        while offset < total:
            # Actualizar la URL con el límite y el offset
            paginated_url = f"{url}&limit={limit}&offset={offset}"
            _logger.info(f"Making paginated request to: {paginated_url}", 'info')
            
            try:
                response = requests.get(paginated_url, headers=headers)
                response.raise_for_status()  # Verifica si hubo algún error
                data = response.json()  # Obtener los datos en formato JSON
                
                # Agregar los resultados (IDs de los items) a la lista all_item_ids
                item_ids = data.get('results', [])
                all_item_ids.extend(item_ids)

                # Actualizar la paginación
                total = data.get('paging', {}).get('total', 1)  # Total de resultados
                offset += limit  # Aumentar el offset para la siguiente página

                _logger.info(f"Processed page with offset {offset}, total results {total}", 'info')
            
            except requests.exceptions.HTTPError as http_err:
                error_message = f"HTTP error occurred for offset {offset}: {http_err}"
                _logger.info(error_message, 'error')
                errors.append(error_message)
                break
            except Exception as err:
                error_message = f"Other error occurred for offset {offset}: {err}"
                _logger.info(error_message, 'error')
                errors.append(error_message)
                break
        
        return all_item_ids, errors

        
        
        
