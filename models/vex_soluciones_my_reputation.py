from odoo import models, fields, api
import requests
import logging


# Configurar el logger
_logger = logging.getLogger(__name__)

class MyReputation(models.Model):
    _name = 'vex_soluciones.my_reputation'
    _description = 'My Reputation'

    name = fields.Char('Nombre del Vendedor')
    level_id = fields.Char(string='Estado de reputación')
    power_seller_status = fields.Char(string='Estado Power Seller')
    total_sales = fields.Integer(string='Total de ventas')
    cancellations = fields.Integer(string='Cancelaciones')
    ratings_positive = fields.Float(string='Valoraciones positivas')
    ratings_neutral = fields.Float(string='Valoraciones neutrales')
    ratings_negative = fields.Float(string='Valoraciones negativas')
    sales_last_60_days = fields.Integer(string='Ventas en los últimos 60 días')
    claims_rate = fields.Float(string='Tasa de reclamos')
    delayed_orders = fields.Integer(string='Órdenes entregadas con retraso')
    canceled_orders = fields.Integer(string='Órdenes canceladas')
    instance_id = fields.Many2one('vex.instance', string="Instancia")

    @api.model
    def consumir_my_reputation(self):
        for instance in self.env['vex.instance'].search([('store_type','=','mercadolibre')]):
            instance.get_access_token()
            ACCESS_TOKEN = instance.access_token
            user_id = instance.user_id
            #ACCESS_TOKEN = "APP_USR-2822929086258615-021014-90783763e1fba8958605fde10a688981-2205765982"
            url = f"https://api.mercadolibre.com/users/{user_id}"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                user_data = response.json()
                print("Tu USER_ID es:", user_data)
                # Extraemos los valores
                obj = {
                    'name': user_data.get('nickname'),
                    'level_id' : user_data.get('seller_reputation', {}).get('level_id'),
                    'power_seller_status' : user_data.get('seller_reputation', {}).get('power_seller_status'),
                    'total_sales' : user_data.get('seller_reputation', {}).get('transactions', {}).get('total', 0),
                    'cancellations' : user_data.get('seller_reputation', {}).get('transactions', {}).get('canceled', 0),
                    'ratings_positive' : user_data.get('seller_reputation', {}).get('transactions', {}).get('ratings', {}).get('positive', 0.0),
                    'ratings_neutral' : user_data.get('seller_reputation', {}).get('transactions', {}).get('ratings', {}).get('neutral', 0.0),
                    'ratings_negative' : user_data.get('seller_reputation', {}).get('transactions', {}).get('ratings', {}).get('negative', 0.0),
                    'sales_last_60_days' : user_data.get('seller_reputation', {}).get('metrics', {}).get('sales', {}).get('completed', 0),
                    'claims_rate' : user_data.get('seller_reputation', {}).get('metrics', {}).get('claims', {}).get('rate', 0.0),
                    'delayed_orders' : user_data.get('seller_reputation', {}).get('metrics', {}).get('delayed_handling_time', {}).get('value', 0),
                    'canceled_orders' : user_data.get('seller_reputation', {}).get('metrics', {}).get('cancellations', {}).get('rate', 0.0),
                    'instance_id' : instance.id
                }
                
                new_register = self.env['vex_soluciones.my_reputation'].create(obj)
                if new_register:
                    _logger.info("Se creo con exito: %s", user_data.get('nickname'))
                else:
                    _logger.info("No se pudo crear el registro: %s", user_data.get('nickname'))
            else:
                print("Error al obtener el USER_ID:", response.status_code, response.json())