from odoo import models, fields, api

class VexAutoResponse(models.Model):
    _name = 'vex.auto.response'


    isRuleActive = fields.Boolean(default = False)
    userInput = fields.Char()
    autoAnswer = fields.Char()    
    ruleType = fields.Selection([
        ('contains', 'Text contains'),
        ('exact', 'Exact'),
        ('ends_with', 'Ending the word'),
        ('starts_with', 'Starting with the word')
    ], string="Rule Type", required=True, default='contains')

    #GPT
    enable_gpt_responder = fields.Boolean(default=False)
    chatgpt_key = fields.Char(string="ChatGPT Key")



    @api.model
    def get_rule_by_id(self, response_id):
        # Obtiene el registro específico utilizando el ID proporcionado
        record = self.search([('id', '=', response_id)], limit=1)
        if record:
            return {
                'id': record.id,
                'ruleActive': record.isRuleActive,
                'userInput': record.userInput,
                'autoResponse': record.autoAnswer,          
                'ruleType': record.ruleType
            }
        else:
            return None  # Si no se encuentra el registro


    @api.model
    def deleteRule(self, record_id):
        # Buscar el registro en 'vex.auto.response' usando el id  
        record_to_delete = self.search([('id', '=', record_id)], limit=1)
        
        # Verificar si el registro existe y eliminarlo
        if record_to_delete.exists():
            record_to_delete.unlink()
            return True  # El registro fue eliminado con éxito
        else:
            return False  # El registro no existe


    @api.model
    def create_auto_response_entry(self, user_input, auto_answer, rule_type='greeting', is_rule_active=True):
         # Crear un nuevo registro en 'vex.auto.response' con los valores especificados
        
        new_entry = self.env['vex.auto.response'].create({
            'isRuleActive': is_rule_active,
            'userInput': user_input,
            'autoAnswer': auto_answer,          
            'ruleType': rule_type
        })
        return new_entry
    
    @api.model
    def get_auto_responses(self):
        # Obtiene los datos de todos los registros y los convierte en un formato que OWL pueda interpretar
        records = self.search([])
        return [{
            'id': record.id, 
            'ruleActive': record.isRuleActive,
            'userInput': record.userInput,
            'autoResponse': record.autoAnswer,          
            'ruleType': record.ruleType
        } for record in records]
    

    @api.model
    def set_rule_active_status(self, rule_id, is_active):
        # Busca el registro por su ID
        record = self.search([('id', '=', rule_id)], limit=1)

        if record:
            # Cambia el estado de 'isRuleActive' según el valor de is_active
            record.write({'isRuleActive': is_active})
            # Regresa un mensaje con el estado actualizado
            return f"El estado del registro con ID {record.id} se cambió a {is_active}.   {rule_id}"
        else:
            return f"Registro con ID {rule_id} no encontrado."
        

    @api.model
    def update_rule(self, response_id, isRuleActive=None, userInput=None, autoAnswer=None, ruleType=None):
        # Verificar que todos los valores necesarios estén presentes
        if isRuleActive is None or userInput is None or autoAnswer is None or ruleType is None:
            return {
                'status': 'error',
                'message': 'Missing one or more required values'
            }
        
        # Buscar el registro por el ID proporcionado
        record = self.search([('id', '=', response_id)], limit=1)
        
        if record:
            # Crear un diccionario con los campos a actualizar
            update_values = {
                'isRuleActive': isRuleActive,
                'userInput': userInput,
                'autoAnswer': autoAnswer,
                'ruleType': ruleType
            }

            # Actualizar los valores de los campos
            record.write(update_values)

            return {
                'status': 'success',
                'message': 'Rule updated successfully',
                'updated_fields': update_values
            }
        else:
            return {
                'status': 'error',
                'message': 'Rule not found'
            }

