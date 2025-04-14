from odoo import models, fields, api

class VexGptConfig(models.Model):
    _name = 'vex.gpt.config'
    
    enable_gpt_responder = fields.Boolean(default=False)
    chatgpt_key = fields.Char(string="ChatGPT Key")
    daily_usage_limit = fields.Integer(string="Daily Usage Limit", default=1000)  # Límite diario


    @api.model
    def get_gpt_config(self):
        """
        Returns the values of 'enable_gpt_responder' and 'chatgpt_key'.
        """
        config = self.search([], limit=1)
        return {
            'enable_gpt_responder': config.enable_gpt_responder if config else False,
            'chatgpt_key': config.chatgpt_key if config else '',
            'daily_usage_limit': config.daily_usage_limit if config else 0
        }
    

    @api.model
    def update_gpt_config(self, enable_gpt_responder):
        """
        Updates the value of 'enable_gpt_responder'.

        :param enable_gpt_responder: New value for the boolean field.
        :return: True if the operation was successful, False otherwise.
        """
        config = self.search([], limit=1)
        if not config:
            # Create a new record if none exists
            self.create({'enable_gpt_responder': enable_gpt_responder})
        else:
            # Update the existing record
            config.write({'enable_gpt_responder': enable_gpt_responder})
        return True
    

    @api.model
    def update_gpt_config(self, enable_gpt_responder=None, chatgpt_key=None, daily_usage_limit=None):
        """
        Updates the values of 'enable_gpt_responder', 'chatgpt_key', and 'daily_usage_limit'.

        :param enable_gpt_responder: New value for the boolean field (optional).
        :param chatgpt_key: New value for the 'chatgpt_key' field (optional).
        :param daily_usage_limit: New value for the 'daily_usage_limit' field (optional).
        :return: True if the operation was successful.
        """
        config = self.search([], limit=1)
        if not config:
            # Create a new record if none exists
            values = {
                'enable_gpt_responder': enable_gpt_responder if enable_gpt_responder is not None else False,
                'chatgpt_key': chatgpt_key or '',
                'daily_usage_limit': daily_usage_limit or 1000,
            }
            self.create(values)
        else:
            # Update the existing record with provided values
            update_values = {}
            if enable_gpt_responder is not None:
                update_values['enable_gpt_responder'] = enable_gpt_responder
            if chatgpt_key is not None:
                update_values['chatgpt_key'] = chatgpt_key
            if daily_usage_limit is not None:
                update_values['daily_usage_limit'] = daily_usage_limit

            config.write(update_values)
        return True