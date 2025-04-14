from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests

import logging
_logger = logging.getLogger(__name__)

class ProductTemplateInherit(models.Model):
    _inherit         = "product.template"

    @api.model
    def get_products_closed_from_meli(self):
        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id
        
        ACCESS_TOKEN = meli_instance.access_token
        USER_ID = meli_instance.user_id
        items = []
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

        url_get_items = f"https://api.mercadolibre.com/users/{USER_ID}/items/search?status=closed"
        res_items = requests.get(url_get_items, headers=headers)

        if res_items.status_code == 200:
            data_response_items = res_items.json()
            for i in data_response_items['results']:
                url_get_data_items = f"https://api.mercadolibre.com/items/{i}"
                res_data = requests.get(url_get_data_items, headers=headers)
                if res_data.status_code == 200:
                    data_response = res_data.json()
                    existing_record = self.search([('meli_id', '=', data_response['id'])], limit=1)
                    if existing_record:
                        existing_record.write({
                            'title': data_response['title'],
                            'image_url': data_response['thumbnail'],
                            'price': data_response['price'],
                            'listing_type': data_response['listing_type_id'],
                            'condition': data_response['condition'],
                            'stop_date': data_response['stop_time'],
                            'quantity': data_response['available_quantity']
                        })
                    else:
                        self.create({
                            'meli_id': data_response['id'],
                            'title': data_response['title'],
                            'image_url': data_response['thumbnail'],
                            'price': data_response['price'],
                            'listing_type': data_response['listing_type_id'],
                            'condition': data_response['condition'],
                            'stop_date': data_response['stop_time'],
                            'quantity': data_response['available_quantity'],
                            'state': 'pending'
                        })
                    print(data_response.get('id'))
                    print("hola")
                    items.append(data_response)
                else:
                    print(f"Error {res_items.status_code}: {res_items.text}")
                    return "Error al obtener datos de la API"
            return items
        else:
            print(f"Error {res_items.status_code}: {res_items.text}")
            return "Error al obtener datos de la API"
    
    def exec_republish_items(self):
        if not self:
            raise UserError("You have not selected any record.")
        registros_invalidos = self.filtered(lambda r: r.meli_status != 'closed')
        if registros_invalidos:
            raise UserError("You can only run this action on Status ML records 'Closed'.")
        
        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id
        
        ACCESS_TOKEN = meli_instance.access_token
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

        for rec in self:
            data = { 
                "price": rec.list_price,
                "quantity": rec.instance_id.default_quantity_republish,
                "listing_type_id": rec.listing_type_id
                } 
            url_republish = f"https://api.mercadolibre.com/items/{rec.default_code}/relist"
            response = requests.post(url_republish, headers=headers, json=data)
            response_json = response.json()
            if response_json['status']=="active":
                rec.write({
                    'default_code':response_json['id'],
                    'ml_publication_code':response_json['id'],
                    'meli_status': 'active'
                })
            else:
                print(f"Error {response_json['status']}: {response_json['message']}")
                raise UserError( f"Error {response_json['status']}: {response_json['message']}")

    @api.model
    def cron_republish_items(self):
        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id
        #meli_instance = self.env['vex.instance'].search([('name', '=', 'Tienda test dos')])
        if meli_instance.auto_republish:
            items_closed = self.search([('meli_status', '=', 'closed')])
            if items_closed:
                items_closed.exec_republish_items()
        
class VexInstanceInherit(models.Model):
    _inherit         = "vex.instance"


    auto_republish = fields.Boolean('auto_republish')
    default_quantity_republish = fields.Integer('default_quantity_republish')
