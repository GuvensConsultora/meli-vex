from odoo import api, fields, models

class VexResPartner(models.Model):
    _inherit         = "res.partner"

    meli_code = fields.Char('Código ML')
    server_meli = fields.Boolean('server_meli')
    nickname = fields.Char('NickNameML')
    meli_user_id = fields.Char("User ID in Mercado Libre", index=True, help="Unique user ID from Mercado Libre")
    store_type = fields.Char("Store Type")

    instance_id = fields.Many2one('vex.instance', string='Instance')