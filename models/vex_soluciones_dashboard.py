from odoo import api, fields, models

class VexDashboardData(models.Model):    
    _name="vex.dashboard.data"
    _description = 'Dashboard save data'

    month = fields.Char("Month", required=True)
    year = fields.Integer("Year", required=True)
    new_customers = fields.Integer("New Customers", required=True)
    last_updated = fields.Datetime("Last Updated", default=fields.Datetime.now)
    data_for = fields.Char("Data For") 
    extra_data = fields.Json(string="Extra Data")  # Declaración del campo extra_data
    
    instance_id = fields.Many2one('vex.instance', string='Instance')
