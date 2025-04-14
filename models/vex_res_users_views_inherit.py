from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    is_question_responder = fields.Boolean(string="Is Question Responder")
