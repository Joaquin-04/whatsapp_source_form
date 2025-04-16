# -*- coding: utf-8 -*-
import logging
import json
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
    
    formulario_sent = fields.Boolean(string="Formulario Enviado", default=False,
                                     help="Indica si ya se envió el mensaje interactivo de formulario.")

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        _logger.info("Entrando en _notify_thread con message: %s, msg_vals: %s, kwargs: %s",
                     message, msg_vals, kwargs)
        res = super()._notify_thread(message, msg_vals, **kwargs)
        
        # Para testing: reiniciamos formulario_sent para forzar envío
        self.formulario_sent = False

        if self.channel_type == 'whatsapp' and not self.formulario_sent:
            try:
                _logger.info("Canal es WhatsApp y formulario no enviado. Enviando mensaje interactivo...")
                self._send_whatsapp_template()
                self.formulario_sent = True
                _logger.info("Formulario enviado exitosamente.")
            except Exception as e:
                _logger.error("Error al enviar formulario: %s", str(e))
        
        # Captura de respuesta del botón interactivo (cuando se recibe webhook)
        if msg_vals and 'interactive' in msg_vals:
            button_reply = msg_vals['interactive'].get('button_reply')
            if button_reply:
                _logger.info("Respuesta interactiva recibida: %s", button_reply)
                self._process_button_response(button_reply.get('id'))  # Usa el 'id' del botón

        return res

    def _send_whatsapp_template(self):
        try:
            # Definimos los botones (asegurate de que cada título tenga máximo 20 caracteres)
            buttons = [
                {'title': 'Google', 'payload': 'google'},
                {'title': 'Facebook', 'payload': 'social'},
                {'title': 'Landing', 'payload': 'landing'}
            ]
            _logger.debug("Botones definidos: %s", buttons)
            
            # Creamos el mensaje base en mail.message (este registro sirve para vincular el mensaje a un hilo en Odoo)
            mail_message = self.env['mail.message'].create({
                'model': 'discuss.channel',
                'res_id': self.id,
                'body': 'Enviando mensaje interactivo Formulario',
            })
            _logger.debug("Mensaje base creado: %s", mail_message)
            
            # Preparamos el payload para WhatsApp con los parámetros exigidos por la API:
            whatsapp_payload = self._prepare_interactive_message(
                body="Para brindarte mejor atención, ¿dónde nos encontraste?",
                buttons=buttons
            )
            _logger.info("Payload de WhatsApp preparado:\n%s", json.dumps(whatsapp_payload, indent=2))
            
            # Creamos el registro de whatsapp.message (este registro queda ligado al mail.message, pero su contenido no es usado para armar el payload)\n
            whatsapp_msg = self.env['whatsapp.message'].create({
                'mobile_number': f"{self.whatsapp_number}",  # Asegurate de que esté en formato E.164, ej: '+5493874880449'
                'wa_account_id': self.wa_account_id.id,
                'message_type': 'outbound',  # Los mensajes salientes siempre son 'outbound'
                'mail_message_id': mail_message.id,
                # El campo body no se utiliza para construir el payload, pero se registra para referencia
                'body': whatsapp_payload.get('interactive', {}).get('body', {}).get('text', '')
            })
            _logger.debug("Registro de whatsapp.message creado: %s", whatsapp_msg)
            
            # Enviar el mensaje a través de la API de WhatsApp
            wa_api = WhatsAppApi(self.wa_account_id)
            _logger.info("Enviando mensaje interactivo desde cuenta %s, número: %s",
                         self.wa_account_id.name, self.whatsapp_number)
            msg_uid = wa_api._send_whatsapp(
                number=f"{self.whatsapp_number}",
                message_type='interactive',
                send_vals=whatsapp_payload
            )
            _logger.info("UID recibido: %s", msg_uid)
            
            if msg_uid:
                whatsapp_msg.write({
                    'state': 'sent',
                    'msg_uid': msg_uid
                })
                _logger.info("Mensaje interactivo actualizado a estado 'sent' con UID: %s", msg_uid)
            else:
                _logger.warning("No se recibió UID del mensaje interactivo.")
        
        except Exception as e:
            _logger.error("Error enviando mensaje interactivo: %s", str(e))
            raise    
    
    def _process_button_response(self, button_id):
        """ Mapea la respuesta del botón al campo source_option. """
        mapping = {
            'google': 'google',
            'social': 'social',
            'landing': 'landing',
        }
        self.source_option = mapping.get(button_id)
        _logger.info("source_option actualizado a: %s", self.source_option)

    def _prepare_interactive_message(self, body, buttons):
        """
        Prepara el payload para enviar un mensaje interactivo con botones (respuesta rápida) según WhatsApp Cloud API.
        :param body: Texto del cuerpo del mensaje.
        :param buttons: Lista de diccionarios con 'title' y 'payload'.
        :return: Diccionario con la estructura esperada por la API.
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": f"+{self.whatsapp_number}",  # Asegurate de que el número esté en formato E.164, ej: '+5493874880449'
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                # Opcional: incluir 'header' o 'footer' si se necesitan\n
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": btn["payload"],
                                "title": btn["title"]
                            }
                        } for btn in buttons
                    ]
                }
            }
        }
        return payload
