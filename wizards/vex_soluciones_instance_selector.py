from odoo import models, fields, api, http
import logging
_logger = logging.getLogger(__name__)

class InstanceSelectorWizard(models.TransientModel):
    _name = 'instance.selector.wizard'
    _description = 'Wizard para seleccionar instancia'

    instance_id = fields.Many2one('vex.instance', string="Instance", required=True, default=lambda self: self.env.user.meli_instance_id)
    
    def apply_instance(self):
        _logger.info("apply_instance")
        self.ensure_one()  # buena práctica si estás trabajando con un solo registro
        self.env.user.write({'meli_instance_id': self.instance_id.id})

        # Devuelve la acción que abre el dashboard
        return {
            'type': 'ir.actions.client',
            'tag': 'vex_sync_mercado_libre.welcome',
            'target': 'current',  # o 'new' si quieres que sea un pop-up
        }

    