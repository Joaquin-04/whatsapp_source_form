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
    ], string="Fuente del Lead", default=False,
       help="Opción seleccionada por el usuario para identificar la fuente del lead.")

    formulario_sent = fields.Boolean(string="Formulario Enviado", default=False,
                                     help="Indica si ya se envió el mensaje interactivo de formulario.")

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        """
        Extiende el método de notificación para los mensajes inbound en canales de WhatsApp.
        Cuando se recibe un mensaje inbound (identificado por 'whatsapp_inbound_msg_uid') se evalúa:
          - Si aún no se ha enviado el formulario, se envía la plantilla 'formulario' como mensaje de texto.
          - Si ya se envió, se verifica si el mensaje entrante coincide con alguna opción permitida y se captura.
        """
        res = super(DiscussChannel, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        
        for channel in self:
            if channel.channel_type == 'whatsapp' and kwargs.get('whatsapp_inbound_msg_uid'):
                allowed_options = ['Google o YouTube', 'Facebook o Instagram', 'Landing Page']
                body_text = message.body.strip() if message.body else ''
                
                _logger.warning(f"allowed_options: {allowed_options} body_text: {body_text} ")
                
                # Buscar la plantilla 'formulario'
                template = self.env['whatsapp.template'].search([('template_name', '=', 'formulario')], limit=1)
                template_text = template.body.strip() if template else ''

                _logger.warning(f"Template: {template} template_text: {template_text} ")
                
                # Evitamos procesar el mensaje si es el mismo que el de formulario
                if body_text == template_text:
                    continue

                if not channel.formulario_sent:
                    _logger.warning(f"Si el formulario no se mando")
                    # Enviar el mensaje interactivo usando la plantilla
                    if template and channel.wa_account_id and channel.whatsapp_number:
                        
                        try:
                            wa_api = WhatsAppApi(channel.wa_account_id)
                            send_vals = {
                                'preview_url': True,
                                'body': template.body,
                            }
                            msg_uid = wa_api._send_whatsapp(
                                number=channel.whatsapp_number,
                                message_type='text',  # Enviamos como texto con el contenido de la plantilla
                                send_vals=send_vals
                            )
                            channel.formulario_sent = True
                            _logger.warning("Formulario interactivo enviado en canal %s, msg_uid: %s", channel.id, msg_uid)
                        except Exception as e:
                            _logger.exception("Error enviando formulario interactivo en canal %s: %s", channel.id, e)
                    else:
                        _logger.warning("No se pudo enviar el formulario en canal %s: falta plantilla, cuenta o número.", channel.id)
                else:
                    # Si el formulario ya fue enviado, procesamos la respuesta inbound
                    if not channel.source_option and body_text in allowed_options:
                        mapping = {
                            'Google o YouTube': 'google',
                            'Facebook o Instagram': 'social',
                            'Landing Page': 'landing',
                        }
                        channel.source_option = mapping.get(body_text)
                        _logger.warning("Fuente capturada en canal %s: %s", channel.id, channel.source_option)
        return res


