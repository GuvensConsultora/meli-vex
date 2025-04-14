# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


_logger = logging.getLogger(__name__)

class VexQuestionsMeli(models.Model):
    _name = "vex.meli.questions"
    _description = "Questions Vex Meli"

    name = fields.Char(required=True, string="Name")

    # Mercado libre fields
    meli_created_at = fields.Datetime()
    meli_item_id = fields.Char()
    meli_seller_id = fields.Char()
    meli_status = fields.Char()
    meli_text = fields.Char()
    meli_id = fields.Char(required=True)
    meli_deleted_from_listing = fields.Boolean()
    meli_hold = fields.Boolean()
    meli_answer = fields.Char()
    meli_from_id = fields.Char()
    meli_import_type = fields.Char()
    meli_answered_from_odoo = fields.Boolean()
    meli_odoo_answerer = fields.Char()
    meli_from_nickname = fields.Char()
    meli_answered_at = fields.Datetime()
    meli_instance_id = fields.Many2one('vex.instance', string="Instancia", required=True)


    @api.model
    def create(self, vals):
        record = super(VexQuestionsMeli, self).create(vals)   
        self.env['bus.bus']._sendone(
            (self.env.cr.dbname, 'vex_meli_questions_update'),  # Canal
            'notification_type',  # Tipo de notificación (reemplaza con el tipo adecuado)
            {'message': 'Questions updated'}  # Mensaje
        )


        return record

    def write(self, vals):
        
        res = super(VexQuestionsMeli, self).write(vals)
        # self.env['bus.bus']._sendone(
        #     (self.env.cr.dbname, 'vex_meli_questions_update'),  # Canal
        #     'notification_type',  # Tipo de notificación (reemplaza con el tipo adecuado)
        #     {'message': 'Questions updated'}  # Mensaje
        # )

        #Como 
        meli_question_ids = [record.meli_id for record in self]
        self.update_channel_messages(meli_question_ids)

        return res
    
    def update_channel_messages(self,meli_question_ids ):
        _logger.info(f"Writing a meli question: {meli_question_ids}")
        # Busca el canal específico por nombre
        channel = self.env['discuss.channel'].sudo().search([('name', '=', "Questions for Mercado Libre")], limit=1)
        
        if channel:
            # Busca todos los mensajes del canal
            messages = self.env['mail.message'].sudo().search([('res_id', '=', channel.id)])

            # Variable con la que deseas comparar
            _logger.info(f"Variable to match: {meli_question_ids}") 

            for message in messages:
                # Lee el sujeto del mensaje
                subject = message.subject or ""

                # Extrae el número del subject
                if "Nueva pregunta en Mercado Libre-" in subject:
                    try:
                        # Divide y extrae el número después del guion
                        extracted_number = subject.split("Nueva pregunta en Mercado Libre-")[-1]
                        _logger.info(f"Extracted number: {extracted_number}")
                        
                        # Compara con la otra variable
                        if extracted_number in meli_question_ids:
                            # Borra el registro si coincide
                            _logger.info(f"Matched message: {message}")
                            message.unlink()
                            _logger.info(f"Message deleted: {message}") 
                    except Exception as e:
                        # Loguea el error en caso de problemas
                        _logger.error(f"Error al procesar el mensaje: {e}")

    
    def _log(self, message, level='info'):
        if True:
            if isinstance(message, list):
                message = ' - '.join(message)
            log_method = getattr(_logger, level, _logger.info)
            log_method(message)
            try:
                print(message)
            except UnicodeEncodeError:
                print(message.encode('utf-8', errors='replace').decode('utf-8'))
            
            try:
                self.env['vex.log'].create({
                    'name': message,
                    'level': level,                    
                    'instance_id': 1, # self.meli_id  Se forza un 1 para tener una instancia , pero si hay multiples instancias no funcionara PROBLEMA DE SELF
                    'date': fields.Datetime.now(),
                })
            except Exception as ex:
                log_method(f"Error creating log: {str(ex)}")

  

    def multiple_create_if_not_exists(self, data):
        """
        Crea múltiples registros en la base de datos si no existen previamente.
        Retorna un diccionario con los resultados de cada operación.
        """
        results = {
            "created": [],
            "existing": [],
            "errors": []
        }

        for val in data:
            try:
                # Verificar si ya existe el registro
                existing = self.search([('meli_id', '=', val['meli_id'])])
                if not existing:
                    created_record = self.create(val)
                    results["created"].append({"id": created_record.id, "meli_id": val['meli_id']})
                    _logger.info(f"Pregunta creada: {val['meli_id']}")
                else:
                    results["existing"].append({"id": existing.id, "meli_id": val['meli_id']})
                    _logger.info(f"Pregunta ya existente con meli_id: {val['meli_id']}")
            except Exception as e:
                results["errors"].append({"meli_id": val.get('meli_id', 'unknown'), "error": str(e)})
                _logger.error(f"Error al procesar la pregunta con meli_id: {val.get('meli_id', 'unknown')}. Detalle: {e}")

        return results            

    @api.model
    def get_question_count(self):
        """
        Retorna el número total de preguntas en el sistema.
        """
        current_user = self.env.user 
        question_count = self.search_count([('meli_instance_id', '=', current_user.meli_instance_id.id)])
        _logger.info(f"Número total de preguntas: {question_count}")
        return question_count
    

    @api.model
    def get_questions_count_by_category(self):
        """
        Cuenta las preguntas agrupadas por categoría del producto vinculado
        (usando ml_publication_code) e incluye el nombre de la categoría.
        Los datos se almacenan o actualizan en la base de datos.
        """
        DashboardData = self.env['vex.dashboard.data']
        data_for = "questions_count_by_category"
        current_user = self.env.user 

        # Buscar registro existente
        record = DashboardData.search([('data_for', '=', data_for)], limit=1)
        if not record or record.last_updated < datetime.now() - timedelta(days=1):
            questions = self.search([('meli_instance_id', '=', current_user.meli_instance_id.id)])
            product_model = self.env['product.template']

            # Contenedor para agrupar las preguntas por categoría
            category_question_data = {}

            for question in questions:
                product = product_model.search([('ml_publication_code', '=', question.meli_item_id), ('instance_id', '=', current_user.meli_instance_id.id)], limit=1)
                if product and product.categ_id:  # Usar categ_id en lugar de un código personalizado
                    category_id = product.categ_id.id
                    if category_id not in category_question_data:
                        # Obtener el nombre de la categoría
                        category_name = product.categ_id.name or 'Desconocido'
                        category_question_data[category_id] = {
                            'category_name': category_name,
                            'question_count': 0
                        }
                    # Incrementar el contador de preguntas para esta categoría
                    category_question_data[category_id]['question_count'] += 1

            # Convertir a un formato más usable (lista de diccionarios) y ordenar por conteo descendente
            sorted_data = sorted(
                [
                    {
                        'category_id': category_id,
                        'category_name': data['category_name'],
                        'question_count': data['question_count']
                    }
                    for category_id, data in category_question_data.items()
                ],
                key=lambda x: x['question_count'],
                reverse=True
            )

            # Tomar solo las 5 categorías principales
            top_5_categories = sorted_data[:5]

            # Crear o actualizar el registro con los datos calculados
            record_data = {
                'month': 'N/A',  # No aplica
                'year': 0,  # No aplica
                'new_customers': 0,  # No aplica
                'last_updated': fields.Datetime.now(),
                'data_for': data_for,
                'extra_data': top_5_categories,  # Guardar los datos en un único campo JSON
                'instance_id': current_user.meli_instance_id.id
            }
            if record:
                record.write(record_data)
            else:
                DashboardData.create(record_data)

            return top_5_categories

        # Retornar los datos desde el campo `extra_data`
        return record.extra_data if 'extra_data' in record else []