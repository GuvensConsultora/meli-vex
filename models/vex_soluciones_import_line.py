from odoo import fields, models, api

class VexSolucionesImportLine(models.Model):
    _name="vex.import_line"
    _order = "create_date desc"
    
    start_date = fields.Datetime('Start Date')
    end_date = fields.Datetime('End Date')
    description = fields.Char('Description')
    stock_import = fields.Boolean('Stock import')
    images_import = fields.Boolean('Images import')
    status = fields.Selection([
        ('done', 'Done'),
        ('pending', 'Pending'),
        ('error', 'Error'),('obs', 'Observed')
    ], string='Status')

    instance_id = fields.Many2one('vex.instance', string='Instance id')

    action = fields.Selection([
        ('product', 'Product'),
        ('order', 'Order')
    ], string='Action')
    checks_indicator = fields.Char('Counter')
    result = fields.Char('Result')

    store_type = fields.Selection([
        ('mercadolibre', 'Mercado Libre'),
        ('walmart', 'Walmart')
    ], string="Store Type", required=True, default='mercadolibre')
