from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests

import logging
_logger = logging.getLogger(__name__)

class VexMeliNotices(models.Model):
    _name               = "vex.meli.notices"
    _description        = "Model to access all current and specific communications sent by Mercado Libre"

    meli_notice_id = fields.Char('Notice ID MeLi')
    label = fields.Char('label')
    description = fields.Text(string='description')
    highlighted = fields.Boolean('Is Highlighted?')
    from_date = fields.Char("From date")
    tag_ids = fields.One2many('vex.meli.notice.tag', 'notice_id', string='Tags')
    dismiss_key = fields.Char("Dismiss Key")
    title = fields.Char("Title")

    @api.model
    def get_data_from_meli(self):
        current_user = self.env.user 
        meli_instance = current_user.meli_instance_id
        
        ACCESS_TOKEN = meli_instance.access_token
        limit = 10
        offset = 0
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

        url_notices = f"https://api.mercadolibre.com/communications/notices?limit={limit}&offset={offset}"
        res_notices = requests.get(url_notices, headers=headers)

        if res_notices.status_code == 200:
            data_response_notices = res_notices.json()
            #notice_id = data_response_notices['results'][0]
            return data_response_notices
        else:
            print(f"Error {res_notices.status_code}: {res_notices.text}")
            return "Error al obtener datos de la API"

            #raise Exception(f"Error al obtener datos de la API: {res_notices.status_code}")
        
        
class VexMeliNoticeTag(models.Model):
    _name               = "vex.meli.notice.tag"
    _description        = "Model to management tags in notices"

    notice_id = fields.Many2one('vex.meli.notices', string="Notice")
    tag = fields.Char('Tag')
    type = fields.Char('Type')