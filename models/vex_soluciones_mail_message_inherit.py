from odoo import models, fields, api
import logging
import pprint
import requests
import json
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import pytz




_logger = logging.getLogger(__name__)
MERCADO_LIBRE_URL = "https://api.mercadolibre.com" 
class MailMessage(models.Model):
    _inherit = 'mail.message'

    unique_message_id = fields.Char("Unique ID for message")
    from_marketplace = fields.Boolean("Message comes from an marketplace")

    @api.model
    def create(self, values):
        #_logger.info("Valores enviados a create():\n%s", pprint.pformat(values))

        res_model = values.get('model', '')  
        res_id = values.get('res_id', 0)
        body = values.get('body', '')  

        return super(MailMessage, self).create(values)
    
        #TENEMOS BUG IMPORTANTE POR MENSAJERIA INTERNA EN LA CREACION DE UN SALE ORDER

      

        if hasattr(body, '__html__'):
            body = body.__html__()

        if res_model == 'sale.order' and res_id:
            sale_order = self.env['sale.order'].browse(res_id)
            if sale_order.exists():
                cliente = sale_order.partner_id.name 
                # Obtener todos los campos del cliente
                cliente_res = sale_order.partner_id
                # cliente_datos = {field: getattr(cliente_res, field, 'N/A') for field in cliente_res._fields.keys()}
                
                # # Formatear y loggear todos los datos del cliente
                # _logger.info(f"Todos los datos del Cliente:\n{pprint.pformat(cliente_datos)}")

                numero_orden = sale_order.name  
                _logger.info(f"Mensaje relacionado con la Orden: {numero_orden}, Cliente: {cliente}  Order ID ML: {sale_order.meli_code}")                
                _logger.info(f"Contenido del mensaje: {body}")
                tienda =  self.env['vex.instance'].search([ ('id', '=', sale_order.instance_id.id )], limit=1)
                if tienda:
                    _logger.info(f"Venta para la tienda {tienda.name}  con acces token {tienda.access_token}")
                _logger.info(f"Para la instancia")

                from_marketplace = values.get('from_marketplace',False)
                if not from_marketplace:
                    _logger.info("Significa que viene de sistema de odoo, asi que creamos mensaje en Marketplace")
                    unique_id = None
                    if sale_order.in_mediation:
                        _logger.info("Tenemos que enviar mensaje por mensajeria de Mediation --fixing")
                        claim_id = self.env['vex.soluciones.mercadolibre.claim'].search([('resource_id', '=', sale_order.meli_code)], limit=1).claim_id
                        if claim_id:
                            send_mesasge = self.send_claim_message(claim_id=claim_id, message=str(body), access_token=tienda.access_token)
                            if send_mesasge == 201:
                                _logger.info("Mensaje de mediacion enviado correctamente")
                            else:
                                _logger.info("Error al enviar mensaje de mediacion")
                                raise ValidationError("La reclamacion ha sido tomada por ML y no se puede enviar mensaje al usuario, por favor revisar en la plataforma de ML")
                        else:
                            _logger.info("No se encontro el claim_id")
                            raise ValueError("Error al enviar mensaje de mediacion")
                    else:
                        unique_id = self.send_pos_sale_message(order_id=str(sale_order.meli_code),response=str(body),accessToken=tienda.access_token,seller_id=tienda.user_id,buyer_id=cliente_res.meli_user_id)
                        #Modificamos el autor para que sea el mismo que el de nombre de la tienda
                    author = self.env['res.partner'].search([('name', '=', tienda.nick)], limit=1)
                    if unique_id:
                        values['unique_message_id'] = unique_id
                    values['author_id'] = author.id
                
                 
                    current_utc = datetime.utcnow()

                    # Convertir la hora UTC a la zona horaria local
                    local_timezone = pytz.timezone('America/Mexico_City')
                    current_local = pytz.utc.localize(current_utc).astimezone(local_timezone)
                    final_date = current_local.strftime('%Y-%m-%d %H:%M:%S')
                    _logger.info(f"Hora local para el mensaje: {final_date}")

                    # Asignar a values['date'] (naive sin tzinfo o formateado como string)
                    values['date'] = final_date
    
        
        return super(MailMessage, self).create(values)



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

            response_data = json.loads(answered.text)
            message_id = response_data["id"]
            return message_id

        except requests.RequestException as e:
            _logger.info(f"Error al responder la pregunta: {str(e)}")
            # Agrega logging para verificar la respuesta
            _logger.info(f"Respuesta de la API: {answered.status_code}")
            _logger.info(f"Contenido de la respuesta: {answered.text}")
            
        _logger.info(f"Factura a la orden {order_id} enviada correctamente.")

        

    def send_claim_message(self, claim_id: str, message: str, access_token: str):
        """
        Envía un mensaje relacionado con un reclamo en Mercado Libre.
        
        :param claim_id: ID del reclamo
        :param message: El mensaje que deseas enviar
        :param access_token: Token de acceso de la API de Mercado Libre
        :return: ID del mensaje enviado o None en caso de error
        """
        _logger.info(f"Iniciando envío de mensaje para el reclamo {claim_id}")

        # URL del endpoint para mensajes de reclamos
        url = f"https://api.mercadolibre.com/post-purchase/v1/claims/{claim_id}/actions/send-message"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        try:
            # Cuerpo de la solicitud
            body = {
                "receiver_role": "complainant",  # Siempre enviamos mensajes al comprador
                "message": message  # El mensaje que queremos enviar
            }

            # Agrega logging para depuración
            _logger.info(f"URL de la solicitud: {url}")
            _logger.info(f"Headers de la solicitud: {headers}")
            _logger.info(f"Body de la solicitud: {body}")

            # Realiza la solicitud POST al endpoint
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()  # Genera una excepción si hay un error en la solicitud
            
            _logger.info(f"Respuesta exitosa")
            _logger.info(f"Respuesta de la API: {response.status_code}")
            _logger.info(f"Contenido de la respuesta: {response.text}")

            # Analiza la respuesta
            response_data = response.status_code
            return response_data

        except requests.RequestException as e:
            # Manejo de errores y logging
            _logger.error(f"Error al enviar el mensaje para el reclamo {claim_id}: {str(e)}")
            if 'response' in locals():
                _logger.error(f"Respuesta de la API: {response.status_code}")
                _logger.error(f"Contenido de la respuesta: {response.text}")

        return None
