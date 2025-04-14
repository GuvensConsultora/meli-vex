from odoo import api, fields, models, _

class VexRestapilist(models.Model):
    _name                = "vex.restapi.list"
    _description         = "List Vex RestApi"


    def _generate_count(self):
        for record in self:
            model = record.model
            if model:
                
                if model =='product.pricelist':
                    count = self.env[str(model)].search_count([('server_meli', '!=', False)])
                else:
                    count = self.env[str(model)].search_count([('server_meli', '!=', False), ('meli_code', '!=', False)])
                if model == "res.partner":
                    count = self.env[str(model)].search_count([('server_meli', '!=', False), ('nickname', '!=', False)])
                    
                record.total_count = count
            else:
                record.total_count = 0


    name                 = fields.Char(required=True)
    argument             = fields.Char()
    model                = fields.Char()
    # log                  = fields.One2many('vex.logs','vex_list')
    interval             = fields.Integer(default=60)
    interval_type        = fields.Selection([('minutes', 'Minutes'),('hours', 'Hours'),
                                      ('days', 'Days'),('weeks', 'Weeks'),('months', 'Months')],default='minutes')
    active_cron          = fields.Boolean(default=False)
    interval_stock       = fields.Integer(default=60)
    interval_type_stock  = fields.Selection([('minutes', 'Minutes'), ('hours', 'Hours'),
                                      ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')], default='minutes')
    active_cron_stock    = fields.Boolean(default=False)
    automatic            = fields.Boolean()
    total_count          = fields.Integer(compute='_generate_count') # compute='_generate_count'
    next_date_cron       = fields.Datetime(string="Next Execution Date") #compute='_generate_next_date'
    next_date_cron_stock = fields.Datetime( string="Next Execution Date") #compute='_generate_next_date_stock'
    export               = fields.Boolean()
    importv              = fields.Boolean()
    per_page = fields.Integer(default=10, required=True, string="Items per page")
    all_items = fields.Boolean(default=True)
    max_items = fields.Integer(string="Maximum number of items to be returned approximately")

    import_by_parts = fields.Boolean()
    conector  = fields.Selection([])
    stock_import = fields.Boolean()
    import_images = fields.Boolean()
    import_images_website = fields.Selection([('save','Save url'),('dowload','Save url and Dowload')])
    limit_action = fields.Integer(default=80)
    last_number_import = fields.Integer(default=0,string="Ultima Cantidad Importada")
    log_ids = fields.One2many('vex.meli.logs', 'vex_restapi_list_id', string='Logs')
    
    # _sql_constraints = [
    #     ('unique_id_argument', 'unique(argument,conector)', 'There can be no duplication of argument in conector')
    # ]

    def go_export_product(self):
        name = _('Export Products to Mercadolibre')
        view_mode = 'form'        
        return {

            'name': name,

            'view_type': 'form',

            'view_mode': view_mode,

            'res_model':'vex.export.product.wizard',

            'type': 'ir.actions.act_window',

            'target': 'new',

        }

    def go_action_list(self):
        name = _('Close Shift')

        view_mode = 'tree,form'        
        return {

            'name': name,

            'view_type': 'form',

            'view_mode': view_mode,

            'res_model':self.model,

            'type': 'ir.actions.act_window',

            'target': 'current',

        }

    def clear_log(self):
        for log in self.log_ids:
            if log.action_type == 'Order':
                log.unlink()
