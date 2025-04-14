from odoo import api, fields, models

class VexMeliAction(models.Model):
    _name               = "vex.meli.action"
    _description        = "Model for list actions"


    name = fields.Char('Name')
    model = fields.Char('Model')
    uri = fields.Char('URL')
