# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi

_logger = logging.getLogger(__name__)

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    source_option = fields.Selection([
        ('google', 'Google o YouTube'),
        ('social', 'Facebook o Instagram'),
        ('landing', 'Landing Page'),
    ], string="Fuente del Lead")
    formulario_sent = fields.Boolean(string="Formulario Enviado", default=False)

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        res = super()._notify_thread(message, msg_vals, **kwargs)
        # Solo para testing
        self.formulario_sent = False

        if self.channel_type == 'whatsapp' and not self.formulario_sent:
            try:
                self._send_whatsapp_template()
                self.formulario_sent = True
            except Exception as e:
                _logger.error(f"Error: {str(e)}")

        # Capturar respuesta del botón por ID
        if msg_vals and 'interactive' in msg_vals:
            button_reply = msg_vals['interactive'].get('button_reply')
            if button_reply:
                self._process_button_response(button_reply.get('id'))  # <--- Usar 'id' en lugar de 'title'

        return res

    def _send_whatsapp_template(self, template):
        """Envía un mensaje interactivo con botones de respuesta rápida."""
        _logger.warning("Preparando mensaje interactivo con botones...")
        
        try:
            # Crear el cuerpo del mensaje
            body = "Para brindarte una mejor atención, ¿nos contás dónde viste nuestro anuncio?"
            buttons = [
                {"type": "reply", "reply": {"id": "google", "title": "Google o YouTube"}},
                {"type": "reply", "reply": {"id": "social", "title": "Facebook o Instagram"}},
                {"type": "reply", "reply": {"id": "landing", "title": "Landing Page"}},
            ]

            # Crear mail.message para vincular
            mail_message = self.env['mail.message'].create({
                'model': 'discuss.channel',
                'res_id': self.id,
                'body': body,
            })

            # Crear mensaje de WhatsApp con botones
            whatsapp_msg = self.env['whatsapp.message'].create({
                'mobile_number': f"+{self.whatsapp_number}",  # Formato E.164
                'wa_account_id': self.wa_account_id.id,
                'message_type': 'outbound',
                'body': body,
                'mail_message_id': mail_message.id,
                'button_ids': [(0, 0, {
                    'button_type': 'quick_reply',
                    'name': button['reply']['title'],
                    'payload': button['reply']['id'],
                }) for button in buttons]
            })
            
            # Enviar el mensaje
            whatsapp_msg._send()
            _logger.warning("¡Mensaje interactivo enviado correctamente!")

        except Exception as e:
            _logger.error(f"Error al enviar mensaje: {str(e)}")
            raise
        
    
    def _process_button_response(self, button_id):
        """Mapea el ID del botón al campo source_option."""
        mapping = {
            'google': 'google',
            'social': 'social',
            'landing': 'landing',
        }
        self.source_option = mapping.get(button_id)