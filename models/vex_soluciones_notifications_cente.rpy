def notify_question_responders(self, subject, message):
        """Enviar una notificación a todos los usuarios con is_question_responder=True"""
        # Buscar usuarios con el campo is_question_responder=True
        users = self.search([('is_question_responder', '=', True)])
        
        # Crear la notificación para cada usuario
        for user in users:
            user.notify_info(subject=subject, message=message)

def notify_info(self, subject, message):
    """Enviar una notificación interna al usuario actual"""
    self.env['mail.message'].create({
        'message_type': 'notification',
        'subtype_id': self.env.ref('mail.mt_comment').id,
        'body': message,
        'subject': subject,
        'partner_ids': [(4, self.partner_id.id)],
    })



    def send_question_responder_notification(self):
        """Función para enviar notificaciones a todos los question responders"""
        subject = "Nueva notificación para Question Responders"
        message = "Hola, tienes una nueva notificación importante para revisar."
        self.notify_question_responders(subject, message)