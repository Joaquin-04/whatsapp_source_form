# -*- coding: utf-8 -*-
import logging
import json
from odoo import models, fields, api
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi

_logger = logging.getLogger(__name__)

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'


    # Eliminar el campo Selection y reemplazar por Many2one a utm.source
    source_id = fields.Many2one(
        'utm.source', 
        string="Fuente del Lead",
        help="Fuente UTM asignada según la respuesta del cliente."
    )
    
    formulario_sent = fields.Boolean(string="Formulario Enviado", default=False,
                                     help="Indica si ya se envió el mensaje interactivo de formulario.")


    def _process_text_response(self, user_response):
        _logger.warning("*"*100)
        _logger.warning(f"_process_text_response" )
        _logger.warning("Estado de formulario_sent: %s", self.formulario_sent)
        _logger.warning(f"user_response: {user_response}")
        # Mapeo de keywords a nombres de utm.source
        keyword_mapping = {
            '1': 'Landing',
            'landing': 'Landing',
            '🪧': 'Landing',
            '2': 'Google Ads',
            'google': 'Google Ads',
            'ads': 'Google Ads',
            '📢': 'Google Ads',
            '3': 'Facebook',
            'facebook': 'Facebook',
            'Facebook': 'Facebook',
            'fb': 'Facebook',
            'FB': 'Facebook',
            'Fb': 'Facebook',
            '📱': 'Facebook',
            'instagram': 'Instagram',
            'Instagram': 'Instagram',
            'ig': 'Instagram',
            'Ig': 'Instagram',
            'IG': 'Instagram',
        }
        
        # Buscar coincidencia en los keywords
        source_name = 'whatsApp'  # Valor por defecto
        for key, value in keyword_mapping.items():
            if key in user_response:
                source_name = value
                break
        
        # Buscar el registro utm.source
        utm_source = self.env['utm.source'].search([('name', 'ilike', source_name)], limit=1)
        if utm_source:
            self.source_id = utm_source.id
            _logger.warning("Fuente UTM asignada: %s", source_name)
        else:
            _logger.warning("No se encontró utm.source para: %s", source_name)

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        res = super()._notify_thread(message, msg_vals, **kwargs)
        _logger.warning("*"*100)
        _logger.warning(f"_notify_thread" )
        _logger.warning("Estado de formulario_sent: %s", self.formulario_sent)
        
        
        if self.channel_type == 'whatsapp':
            # Enviar formulario solo si no se ha enviado
            if not self.formulario_sent:
                try:
                    self._send_whatsapp_template()
                    self.formulario_sent = True
                except Exception as e:
                    _logger.error("Error al enviar formulario: %s", str(e))
            
            # Procesar respuesta del usuario
            if msg_vals and 'body' in msg_vals:
                user_response = msg_vals['body'].strip().lower()
                self._process_text_response(user_response)
        
        return res
    
    def _send_whatsapp_template(self):
        _logger.warning("*"*100)
        _logger.warning(f"_send_whatsapp_template" )
        _logger.warning("Estado de formulario_sent: %s", self.formulario_sent)
        try:
            # Mensaje simple con emojis e instrucciones
            message_body = """
            ¿Dónde nos encontraste? Responde con:
            
            🪧 1 para Landing
            📢 2 para Google Ads
            📱 3 para Facebook/Instagram
            
            O escribe el nombre de la fuente (ej: "Facebook").
            """
            
            # Crear mail.message
            mail_message = self.env['mail.message'].create({
                'model': 'discuss.channel',
                'res_id': self.id,
                'body': message_body,
            })
            
            # Formatear número con '+'
            whatsapp_number = f"+{self.whatsapp_number}" if not self.whatsapp_number.startswith("+") else self.whatsapp_number
            
            # Crear whatsapp.message
            whatsapp_msg = self.env['whatsapp.message'].create({
                'mobile_number': whatsapp_number,
                'wa_account_id': self.wa_account_id.id,
                'message_type': 'outbound',
                'mail_message_id': mail_message.id,
                'body': message_body
            })
            
            # Enviar mensaje de texto
            wa_api = WhatsAppApi(self.wa_account_id)
            msg_uid = wa_api._send_whatsapp(
                number=whatsapp_number,
                message_type='text',
                send_vals={'body': message_body}  # Payload simple
            )
            
            if msg_uid:
                whatsapp_msg.write({'state': 'sent', 'msg_uid': msg_uid})
                _logger.info("Mensaje de texto enviado con UID: %s", msg_uid)
            else:
                _logger.warning("No se recibió UID del mensaje de texto.")
            
            self.formulario_sent = True
        
        except Exception as e:
            _logger.error("Error enviando mensaje de texto: %s", str(e))
            raise

   

