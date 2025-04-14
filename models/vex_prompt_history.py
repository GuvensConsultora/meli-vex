# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class VexPromptHistory(models.Model):
    _name = "vex.prompt.history"
    _description = "GPT Prompt History"


    item_id = fields.Char(required=True, string="ID de la Pregunta")
    question_id = fields.Char(required=True, string="ID de la Pregunta")
    question_text = fields.Text(required=True, string="Texto de la Pregunta")
    gpt_response = fields.Text(string="Respuesta Generada por GPT")
    instance_id = fields.Many2one('vex.instance', string="Instancia", required=True)
    is_answered = fields.Boolean(string="Respondida", default=False)
    processed_at = fields.Datetime(string="Fecha de Procesamiento", default=fields.Datetime.now)
