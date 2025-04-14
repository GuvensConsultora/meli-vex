from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    meli_instance_id = fields.Many2one(
        "vex.instance", 
        string="MercadoLibre Instance",
        store=True,
        default = lambda self: self.env['vex.instance'].search([('store_type', '=', 'mercadolibre')], limit=1).id
    )

    def action_open_meli_instance(self):
        """Redirige al formulario de la instancia relacionada al usuario actual"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "MercadoLibre Instance",
            "res_model": "vex.instance",
            "view_mode": "form",
            "res_id": self.meli_instance_id.id,  # Aquí se pasa el ID correcto
            "target": "current",
            "context": {"default_status": "settings"}
        }