from odoo import models, fields, api
from datetime import datetime, timedelta
import logging




_logger = logging.getLogger(__name__)

class VexAutoResponse(models.Model):
    _name = 'vex.mediations'

    @api.model
    def create_fictitious_authors(self):
        """Crea autores ficticios si no existen."""
        authors = [
            {"name": "Seller part"},
            {"name": "Buyer part"},
            {"name": "Mercado Libre part"},
        ]

        created_authors = []
        for author in authors:
            existing_author = self.env['res.partner'].search([('name', '=', author['name'])], limit=1)
            if not existing_author:
                # Crear el autor ficticio
                new_author = self.env['res.partner'].create({
                    'name': author['name'],
                    'is_company': False,  # Si es un individuo, puedes cambiarlo a True si representa una empresa
                })
                created_authors.append(new_author)

        return True 
    

    @api.model
    def create_messages_for_order(self, meli_order_id, messages):
        """
        Crea múltiples mensajes asociados a una orden, evitando duplicados.
        :param meli_order_id: ID de la orden donde se mostrarán los mensajes
        :param messages: Lista de mensajes a crear, cada uno en formato:
                        {'id': 'unique_message_id', 'fecha_envio': '2024-12-20T22:26:01Z',
                        'remitente': sender_id, 'destinatario': receiver_id, 'texto': 'message text'}
        :return: Lista de mensajes creados o log de mensajes ya existentes
        """
        order = self.env['sale.order'].search([('meli_code', '=', meli_order_id)], limit=1)
        if not order.exists():
            raise ValueError(f"No se encontró la orden con ID {meli_order_id}")

        created_messages = []
        for message_data in reversed(messages):
            unique_message_id = message_data['id']

            fecha_envio = datetime.fromisoformat(message_data['fecha_envio'].replace('Z', '+00:00')).replace(tzinfo=None)
        
            existing_message = self.env['mail.message'].search([
                ('unique_message_id', '=', unique_message_id)], limit=1)

            if existing_message:
                _logger.info(f"El mensaje con ID único '{unique_message_id}' ya existe para la orden {meli_order_id}.")
                continue

            author = self.env['res.partner'].search([('id', '=', message_data['remitente'])], limit=1)
            tienda =  self.env['vex.instance'].search([('user_id', '=', message_data['remitente'])], limit=1)
            
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



            if not author:
                _logger.warning(f"No se encontró un autor con el ID '{message_data['remitente']}'. Creando autor ficticio.")
                author = self.env['res.partner'].create({'name': f'Autor {message_data["remitente"]}'})

            created_message = self.env['mail.message'].create({
                'res_id': order.id, 
                'model': 'sale.order',  
                'body': message_data['texto'],  
                'author_id': author.id,  
                'message_type': 'comment',  
                'date': fecha_envio, 
                'unique_message_id' : unique_message_id,
                'from_marketplace' : True
            })

            created_messages.append(created_message)
            _logger.info(f"Mensaje creado con ID único '{unique_message_id}' para la orden {meli_order_id}.")

        if not created_messages:
            _logger.info(f"No se crearon mensajes nuevos para la orden {meli_order_id}.")
        else:
            _logger.info(f"Se crearon {len(created_messages)} mensajes nuevos para la orden {meli_order_id}.")

        return created_messages
    
    @api.model
    def create_message_for_order(self, meli_order_id, author_name, message_body):
        """
        Crea un mensaje asociado a una orden.
        :param order_id: ID de la orden donde se mostrará el mensaje
        :param author_name: Nombre del autor del mensaje (ejemplo: 'Seller part', 'Buyer part', 'Mercado Libre part')
        :param message_body: Texto del mensaje que se quiere enviar
        :return: El mensaje creado o un mensaje de error si algo falla
        """
        self.create_fictitious_authors()
        # Verificar si la orden existe
        order = self.env['sale.order'].search([('meli_code', '=', meli_order_id)], limit=1)

        if not order.exists():
            raise ValueError(f"No se encontró la orden con ID {meli_order_id}")

        # Buscar al autor por nombre
        author = self.env['res.partner'].search([('name', '=', author_name)], limit=1)
        if not author:
            raise ValueError(f"No se encontró un autor con el nombre '{author_name}'")

        date_30_minutes_ago = (datetime.now() - timedelta(minutes=300)).strftime('%Y-%m-%d %H:%M:%S')

        # Crear el mensaje asociado a la orden
        message = self.env['mail.message'].create({
            'res_id': order.id,  # ID del registro relacionado (orden)
            'model': 'sale.order',  # Modelo relacionado (en este caso, 'sale.order')
            'body': message_body,  # Texto del mensaje
            'author_id': author.id,  # ID del autor del mensaje
            'message_type': 'comment',  # Tipo de mensaje (comentario)
            'date': date_30_minutes_ago,  # Fecha personalizada
        })

        return message