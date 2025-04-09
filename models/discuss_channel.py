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

    def _send_whatsapp_template(self):
        try:
            # Definimos los botones
            buttons = [
                {'title': 'Google o YouTube', 'payload': 'google'},
                {'title': 'Facebook o Instagram', 'payload': 'social'}, 
                {'title': 'Landing Page', 'payload': 'landing'}
            ]
            
            # Creamos el mensaje base
            mail_message = self.env['mail.message'].create({
                'model': 'discuss.channel',
                'res_id': self.id,
                'body': 'Enviando mensaje interactivo',
            })

            # Preparamos el payload para WhatsApp
            whatsapp_payload = self._prepare_interactive_message(
                body="Para brindarte mejor atención, ¿dónde nos encontraste?",
                buttons=buttons
            )

            # Creamos y enviamos el mensaje
            whatsapp_msg = self.env['whatsapp.message'].create({
                'mobile_number': f"+{self.whatsapp_number}",
                'wa_account_id': self.wa_account_id.id,
                'message_type': 'outbound',
                'mail_message_id': mail_message.id,
                'body': whatsapp_payload['interactive']['body']['text']
            })
            
            # Enviamos directamente a través de la API
            wa_api = WhatsAppApi(self.wa_account_id)
            msg_uid = wa_api._send_whatsapp(
                number=f"+{self.whatsapp_number}",
                message_type='interactive',
                send_vals=whatsapp_payload
            )
            
            # Actualizamos el mensaje con el UID recibido
            if msg_uid:
                whatsapp_msg.write({
                    'state': 'sent',
                    'msg_uid': msg_uid
                })

        except Exception as e:
            _logger.error(f"Error enviando mensaje interactivo: {str(e)}")
            raise    
    
    def _process_button_response(self, button_id):
        """Mapea la respuesta del botón al campo source_option."""
        mapping = {
            'google': 'google',
            'social': 'social',
            'landing': 'landing',
        }
        self.source_option = mapping.get(button_id)


    def _prepare_interactive_message(self, body, buttons):
        """
        Prepara el payload para un mensaje interactivo con botones de respuesta rápida
        :param body: Texto del mensaje
        :param buttons: Lista de diccionarios con 'title' y 'payload'
        :return: Diccionario con la estructura esperada por WhatsApp API
        """
        return {
            'type': 'interactive',
            'interactive': {
                'type': 'button',
                'body': {'text': body},
                'action': {
                    'buttons': [{
                        'type': 'reply',
                        'reply': {
                            'id': btn['payload'],
                            'title': btn['title']
                        }
                    } for btn in buttons]
                }
            }
        }
    



    