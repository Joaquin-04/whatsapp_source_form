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
        _logger.warning(f"***************************************************************************** _notify_thread *****************************************************************************+")
        res = super(DiscussChannel, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)

        # 1) Log y chequeo de datos interactivos
        _logger.warning(f"Valores de la variable msg_vals: {msg_vals}")
        if msg_vals and 'interactive' in msg_vals:
            button_reply = msg_vals['interactive'].get('button_reply')
            if button_reply:
                user_selection = button_reply.get('title')  # "Google o YouTube", etc.
                _logger.warning(f"El usuario seleccionó la opción de botón: {user_selection}")
                # Aquí podrías guardar esa opción en el canal correspondiente si ya lo tienes identificado
                # (dependerá de cómo se relacionen 'message' y 'channel')

        # 2) Ahora sí, recorres los canales
        for channel in self:
            if channel.channel_type == 'whatsapp' and kwargs.get('whatsapp_inbound_msg_uid'):
                allowed_options = ['Google o YouTube', 'Facebook o Instagram', 'Landing Page']
                body_text = message.body.strip() if message.body else ''
                
                _logger.warning(f"allowed_options: {allowed_options} body_text: {body_text}")
                
                # Buscar la plantilla 'formulario'
                template = self.env['whatsapp.template'].search([('template_name', '=', 'formulario')], limit=1)
                template_text = template.body.strip() if template else ''
                _logger.warning(f"Template: {template} template_text: {template_text}")
                
                # Evitamos procesar el mensaje si es el mismo que el de formulario
                if body_text == template_text:
                    continue

                # Solo para testear, luego comentar
                channel.formulario_sent = False

                # Enviar formulario si aún no se envió
                if not channel.formulario_sent:
                    _logger.warning("Formulario no se ha enviado todavía")
                    if template and channel.wa_account_id and channel.whatsapp_number:
                        try:
                            whatsapp_msg_vals = {
                                'mobile_number': channel.whatsapp_number,
                                'wa_account_id': channel.wa_account_id.id,
                                'message_type': 'template',
                                'state': 'outgoing',
                                'wa_template_id': template.id,
                            }
                            whatsapp_msg = self.env['whatsapp.message'].create(whatsapp_msg_vals)
                            whatsapp_msg._send()

                            channel.formulario_sent = True
                            _logger.warning(f"Formulario interactivo (template) enviado en canal {channel.id}, whatsapp_msg_id: {whatsapp_msg.id}")
                            """
                            mail_msg = channel.message_post(
                                body=template.body,
                                message_type='whatsapp_message',
                                subtype_xmlid='mail.mt_comment',
                                author_id=self.env.user.partner_id.id,
                            )
                            whatsapp_msg_vals = {
                                'mobile_number': channel.whatsapp_number,
                                'mail_message_id': mail_msg.id,
                                'wa_account_id': channel.wa_account_id.id,
                                'message_type': 'outbound',
                                'state': 'outgoing',
                                'wa_template_id': template.id,
                            }
                            
                            whatsapp_msg = self.env['whatsapp.message'].create(whatsapp_msg_vals)
                            whatsapp_msg._send()
                            """

                            channel.formulario_sent = True
                            _logger.warning("Formulario interactivo (template) enviado en canal %s, whatsapp_msg_id: %s", channel.id, whatsapp_msg.id)
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

        # 3) Mover el return al final
        return res

