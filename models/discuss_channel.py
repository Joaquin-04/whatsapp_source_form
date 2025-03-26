# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    source_option = fields.Selection([
         ('google', 'Google o YouTube'),
         ('social', 'Facebook o Instagram'),
         ('landing', 'Landing Page'),
    ], string="Fuente del Lead", default=False,
       help="Opción seleccionada por el usuario para identificar la fuente del lead.")
    
    formulario_sent = fields.Boolean(string="Formulario Enviado", default=False,
                                     help="Indica si ya se envió el mensaje interactivo de formulario.")

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """
        Se extiende el método de notificación para los mensajes entrantes en canales de WhatsApp.
        Cuando se recibe un mensaje inbound (identificado por 'whatsapp_inbound_msg_uid') se evalúa:
          - Si aún no se envió el formulario: se envía el mensaje interactivo basado en la plantilla 'formulario'.
          - Si ya se envió, se verifica si el contenido del mensaje coincide con alguna opción permitida,
            para capturar la fuente y almacenarla en el campo 'source_option'.
        """
        res = super(DiscussChannel, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        
        for channel in self:
            if channel.channel_type == 'whatsapp' and kwargs.get('whatsapp_inbound_msg_uid'):
                # Definimos la plantilla interactiva que se sincronizó en Odoo.
                # Se asume que existe una plantilla en el modelo 'whatsapp.template' con template_name 'formulario'
                template = self.env['whatsapp.template'].search([('template_name', '=', 'formulario')], limit=1)
                # Texto de opciones para cotejar con la respuesta (puede ajustarse si se envían botones interactivos)
                allowed_options = ['Google o YouTube', 'Facebook o Instagram', 'Landing Page']
                body_text = message.body.strip() if message.body else ''
                
                # Si el mensaje entrante es el mismo que el de formulario, no se procesa (para evitar bucles)
                if template and body_text == template.body.strip():
                    continue

                if not channel.formulario_sent:
                    # Envío del mensaje interactivo (plantilla) de formulario
                    if template:
                        # Se invoca la lógica existente de envío de plantillas.
                        # Se asume que el método 'send_message_with_template' está disponible en el modelo 'whatsapp.message'
                        channel.env['whatsapp.message'].send_message_with_template({
                            'to': channel.whatsapp_number,
                            'template_uid': template.wa_template_uid,
                            'language': template.lang_code,
                        })
                        channel.formulario_sent = True
                        _logger.warning("Formulario interactivo enviado en canal %s", channel.id)
                    else:
                        _logger.warning("No se encontró la plantilla 'formulario' en whatsapp.template")
                else:
                    # Si el formulario ya fue enviado, se procesa la respuesta del usuario.
                    # Aquí se captura la opción si el mensaje coincide con alguna de las opciones permitidas.
                    if not channel.source_option and body_text in allowed_options:
                        mapping = {
                            'Google o YouTube': 'google',
                            'Facebook o Instagram': 'social',
                            'Landing Page': 'landing',
                        }
                        channel.source_option = mapping.get(body_text)
                        _logger.warning("Fuente capturada en canal %s: %s", channel.id, channel.source_option)
        return res
