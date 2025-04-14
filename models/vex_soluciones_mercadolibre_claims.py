from odoo import models, fields, api
import base64
import openpyxl
import logging
import re
from io import BytesIO
import requests
from datetime import datetime, timedelta, timezone

_logger = logging.getLogger(__name__)

class ClaimsMercadoLibre(models.TransientModel):
    _name = 'vex.soluciones.mercadolibre.claim'
    _description = 'Model for storing Mercado Libre claims status and info'

    claim_id = fields.Char(string='Claim ID', required=True, help='ID of the claim in Mercado Libre')
    resource_id = fields.Char(string='Resource ID', help='Associated resource ID, typically an order ID')
    status = fields.Selection(
        [('opened', 'Opened'), ('closed', 'Closed'), ('resolved', 'Resolved')],
        string='Status',
        help='Current status of the claim'
    )
    type = fields.Char(string='Type', help='Type of the claim (e.g., mediations)')
    stage = fields.Selection(
        [('claim', 'Claim'), ('mediation', 'Mediation'), ('dispute', 'Dispute')],
        string='Stage',
        help='Stage of the claim process'
    )
    reason_id = fields.Char(string='Reason ID', help='Reason code for the claim')
    fulfilled = fields.Boolean(string='Fulfilled', help='Indicates if the claim was fulfilled')
    quantity_type = fields.Selection(
        [('partial', 'Partial'), ('total', 'Total')],
        string='Quantity Type',
        help='Type of quantity involved in the claim'
    )
    complainant_id = fields.Char(string='Complainant User ID', help='User ID of the complainant')
    respondent_id = fields.Char(string='Respondent User ID', help='User ID of the respondent')
    site_id = fields.Char(string='Site ID', help='Marketplace site identifier')
    date_created = fields.Datetime(string='Date Created', help='Date when the claim was created')
    last_updated = fields.Datetime(string='Last Updated', help='Date when the claim was last updated')
    resolution = fields.Text(string='Resolution', help='Resolution details of the claim')
    available_actions = fields.Text(string='Available Actions', help='Actions available for the respondent')

    razon_complaiment = fields.Char(string='Complainant reazon', help='User ID of the complainant')

    response_option = fields.Selection([
        ('refund_full', 'Reembolso Total'),
        ('refund_partial', 'Reembolso Parcial'),
        ('external_support', 'Iniciar disputa con mercado libre ⚠'),
    ], string='Acción a tomar')
    partial_reffund_options =  fields.Json(string='Opciones de reembolso parcial')
    refund_full_reason = fields.Text(string='Razón del Reembolso Total')
    refund_partial_amount = fields.Selection(
        selection=[
            ('10', '10%'),
            ('20', '20%'),
            ('30', '30%'),
            ('40', '40%'),
            ('50', '50%'),
            ('60', '60%'),
            ('70', '70%'),
            ('80', '80%'),
            ('90', '90%'),
        ],
        string='Monto del Reembolso Parcial',
        required=True,
        default='10'
    )
    

    refund_partial_reason = fields.Text(string='Razón del Reembolso Parcial')
    external_support_comment = fields.Text(string='Comentario para Soporte Externo')
    instance_id = fields.Many2one('vex.instance', string='Instance id')

    #@api.model
    def action_button_reclamation(self):
        for record in self:
            # Aquí se puede procesar el reembolso completo
            order = self.env['sale.order'].sudo().search([('meli_code', '=', record.resource_id)], limit=1)
            if record.response_option == 'refund_full':
                # Lógica del reembolso completo
                _logger.info("Procesando rembolso completo")
                _logger.info(f"{record.resource_id}     {record.instance_id.access_token}")
                ml_response = self.offer_total_refund(claim_id=record.claim_id,access_token=record.instance_id.access_token)
                if not ml_response:
                    raise ValueError("La opción de respuesta no permite reembolsos completos.")
                else:
                    _logger.info("Aqui cambiamos la mediacion a en proceso o completada, como procese")                    
                    order.sudo().write({'in_mediation': False})
            elif record.response_option == 'refund_partial':
                _logger.info("Procesando rembolso parcial")
                _logger.info(f"{record.resource_id}     {record.instance_id.access_token}  ")
                ml_response = self.offer_partial_refund(claim_id=record.claim_id,access_token=record.instance_id.access_token,percentage=int(record.refund_partial_amount))
                if ml_response:
                    order.sudo().write({'in_mediation': True})
                    order.sudo().write({'expected_resolution': True})
                    _logger.info(F"Se ha ofrecido un reembolso parcial del {record.refund_partial_amount}%.")
                else:
                    raise ValueError("Hubo un error al procesar el reembolso parcial.")
            elif record.response_option == 'external_support':
                _logger.info("Solicitando soporte externo")
                _logger.info(f"{record.resource_id}     {record.instance_id.access_token}  ")
                ml_response = self.open_dispute(claim_id=record.claim_id,access_token=record.instance_id.access_token)
                if ml_response:
                    order.sudo().write({'in_mediation': True})
                    order.sudo().write({'waiting_ml_intervention': True})
                    order.sudo().write({'expected_resolution': False})
                    _logger.info("Se ha solicitado soporte externo.")

            else:
                raise ValueError("La opción de respuesta no permite reembolsos completos.")
            
    def create_order_message(self, meli_order_id,message):
      
        order = self.env['sale.order'].search([('meli_code', '=', meli_order_id)], limit=1)
        if not order.exists():
            raise ValueError(f"No se encontró la orden con ID {meli_order_id}")

        # Current timestamp in UTC
        current_datetime = datetime.now(timezone.utc).replace(tzinfo=None)


        # Prepare message details
        message_text = message
        author = order.partner_id  

        if not author:
            _logger.warning(f"No se encontró un cliente asociado a la orden {meli_order_id}. Asignando autor genérico.")
            author = self.env['res.partner'].create({'name': 'Autor desconocido'})

        # Create the message in Odoo
        created_message = self.env['mail.message'].create({
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

    def offer_total_refund(self, claim_id: str, access_token: str):
        """Ofrece un reembolso total para un reclamo específico."""
        _logger.info(f"[START] Ofreciendo reembolso total para el reclamo {claim_id}")
        
        url = f"https://api.mercadolibre.com/post-purchase/v1/claims/{claim_id}/expected-resolutions/refund"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        
        try:
            response = requests.post(url, headers=headers)
            _logger.info(f"[SUCCESS] Solicitud enviada. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al ofrecer el reembolso total: {str(e)}")
            return None
        
    def offer_partial_refund(self, claim_id: str, access_token: str, percentage: float):
        """Ofrece un reembolso parcial para un reclamo específico."""
        _logger.info(f"[START] Ofreciendo reembolso parcial del {percentage}% para el reclamo {claim_id}")
        
        # URL del endpoint para ofrecer reembolsos parciales
        url = f"https://api.mercadolibre.com/post-purchase/v1/claims/{claim_id}/expected-resolutions/partial-refund"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Payload con el porcentaje seleccionado
        payload = {
            "percentage": percentage
        }
        
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        _logger.debug(f"[INFO] Payload: {payload}")
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            _logger.info(f"[SUCCESS] Solicitud enviada. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al ofrecer el reembolso parcial: {str(e)}")
            return None
        
    def open_dispute(self,claim_id: str, access_token: str):
        """
        Abre una disputa para un reclamo específico en Mercado Libre.
        
        :param claim_id: ID del reclamo para el que se abrirá la disputa.
        :param access_token: Token de acceso de autenticación.
        :return: Respuesta de la API de Mercado Libre o None si ocurre un error.
        """
        _logger.info(f"[START] Abriendo disputa para el reclamo {claim_id}")
        
        # URL del endpoint para abrir una disputa
        url = f"https://api.mercadolibre.com/post-purchase/v1/claims/{claim_id}/actions/open-dispute"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        _logger.debug(f"[INFO] URL: {url}")
        _logger.debug(f"[INFO] Headers: {headers}")
        
        try:
            # Enviar la solicitud POST
            response = requests.post(url, headers=headers)
            _logger.info(f"[SUCCESS] Solicitud enviada. Código de estado: {response.status_code}")
            _logger.debug(f"[DATA] Contenido de la respuesta: {response.text}")
            response.raise_for_status()
            return response.json().get("stage") == "dispute"
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al abrir la disputa: {str(e)}")
            return None
        
    # Antes de ofrecer un reembolso parcial, es necesario consultar el recurso /available-offers para determinar los montos y porcentajes permitidos.

    def get_partial_refund_offers(self, claim_id: str, access_token: str):
        """Obtiene las opciones disponibles para un reembolso parcial."""
        url = f"https://api.mercadolibre.com/post-purchase/v1/claims/{claim_id}/partial-refund/available-offers"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        try:
            _logger.info(f"[START] Obteniendo ofertas de reembolso parcial para el reclamo {claim_id}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            _logger.info(f"[SUCCESS] Ofertas de reembolso parcial obtenidas.Json {response.json()}")
            return response.json()
        except requests.RequestException as e:
            _logger.error(f"[ERROR] Error al consultar ofertas de reembolso parcial: {str(e)}")
            return None
        
    