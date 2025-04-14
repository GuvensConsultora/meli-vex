from odoo import api, fields, models

class VexMeliLogs(models.Model):
    _name           = "vex.meli.logs"
    _order = "start_date desc"

    action_type     = fields.Char('Action')
    start_date      = fields.Datetime()
    end_date        = fields.Datetime()

    state           = fields.Selection([('error', 'Error'),('done', 'Done'),('obs', 'Observed')])
    description     = fields.Char()
    vex_restapi_list_id = fields.Many2one('vex.restapi.list', string='vex_restapi_list')
    
