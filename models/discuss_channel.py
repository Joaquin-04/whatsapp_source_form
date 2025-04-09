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
        _logger.warning(f"Iniciando _notify_thread con message: {message}, msg_vals: {msg_vals}, kwargs: {kwargs}")
        res = super()._notify_thread(message, msg_vals, **kwargs)
        self.formulario_sent = False

        if self.channel_type == 'whatsapp' and not self.formulario_sent:
            _logger.warning("Canal es WhatsApp y formulario no ha sido enviado. Intentando enviar plantilla de WhatsApp.")
            try:
                self._send_whatsapp_template()
                self.formulario_sent = True
                _logger.warning("Formulario enviado exitosamente.")
            except Exception as e:
                _logger.error(f"Error al enviar el formulario: {str(e)}")

        if msg_vals and 'interactive' in msg_vals:
            button_reply = msg_vals['interactive'].get('button_reply')
            if button_reply:
                _logger.warning(f"Respuesta del botón recibida: {button_reply}")
                self._process_button_response(button_reply.get('id'))

        return res

    def _send_whatsapp_template(self):
        _logger.warning("Iniciando _send_whatsapp_template.")
        try:
            buttons = [
                {'title': 'Google', 'payload': 'google'},
                {'title': 'Facebook/IG', 'payload': 'social'},
                {'title': 'Landing', 'payload': 'landing'}
            ]

            _logger.warning(f"Botones definidos: {buttons}")

            mail_message = self.env['mail.message'].create({
                'model': 'discuss.channel',
                'res_id': self.id,
                'body': 'Enviando mensaje interactivo Formulario',
            })
            _logger.warning(f"Mensaje base creado: {mail_message}")

            whatsapp_payload = self._prepare_interactive_message(
                body="Para brindarte mejor atención, ¿dónde nos encontraste?",
                buttons=buttons
            )
            _logger.warning(f"Payload de WhatsApp preparado: {whatsapp_payload}")

            whatsapp_msg = self.env['whatsapp.message'].create({
                'mobile_number': f"+{self.whatsapp_number}",
                'wa_account_id': self.wa_account_id.id,
                'message_type': 'outbound',
                'mail_message_id': mail_message.id,
                'body': whatsapp_payload['interactive']['body']['text']
            })
            _logger.warning(f"Mensaje de WhatsApp creado: {whatsapp_msg}")

            wa_api = WhatsAppApi(self.wa_account_id)
            msg_uid = wa_api._send_whatsapp(
                number=f"+{self.whatsapp_number}",
                message_type='interactive',
                send_vals=whatsapp_payload
            )
            _logger.warning(f"UID del mensaje enviado: {msg_uid}")

            if msg_uid:
                whatsapp_msg.write({
                    'state': 'sent',
                    'msg_uid': msg_uid
                })
                _logger.warning("Estado del mensaje actualizado a 'sent'.")
            else:
                _logger.warning("No se recibió UID del mensaje; el estado no se actualizó.")

        except Exception as e:
            _logger.error(f"Error enviando mensaje interactivo: {str(e)}")
            raise

    def _process_button_response(self, button_id):
        _logger.warning(f"Procesando respuesta del botón con ID: {button_id}")
        mapping = {
            'google': 'google',
            'social': 'social',
            'landing': 'landing',
        }
        self.source_option = mapping.get(button_id)
        _logger.warning(f"source_option actualizado a: {self.source_option}")

    def _prepare_interactive_message(self, body, buttons):
        _logger.warning(f"Preparando mensaje interactivo con body: '{body}' y botones: {buttons}")
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
    



    