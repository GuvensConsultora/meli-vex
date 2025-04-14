from odoo import models, fields
import base64
import openpyxl
import logging
import re
from io import BytesIO

_logger = logging.getLogger(__name__)

class OpenMenuMediation(models.TransientModel):
    _name = 'menu.mediation'
    _description = 'Open menu for mediation'

    ml_order_id = fields.Char(string='Mercado Libre Order ID')
    mediation_status = fields.Selection([
        ('open', 'Open'),
        ('in_process', 'In Process'),
        ('closed', 'Closed'),
    ], string='Mediation Status', default='open')
    mediation_notes = fields.Text(string='Mediation Notes')