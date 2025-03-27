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

        _logger.warning(f"Valores de la variable msg_vals: {msg_vals}")
        # Supongamos que la info del botón llega en msg_vals['interactive']
        if msg_vals and 'interactive' in msg_vals:
            button_reply = msg_vals['interactive'].get('button_reply')
            if button_reply:
                user_selection = button_reply.get('title')  # "Google o YouTube"
                # ya tienes la opción seleccionada
                if user_selection in ['Google o YouTube', 'Facebook o Instagram', 'Landing Page']:
                    ...
        return res
        
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

                
                #Solo para testear luego comentar
                channel.formulario_sent= False

                # Enviar formulario si aún no se envió
                if not channel.formulario_sent:
                    _logger.warning("Formulario no se ha enviado todavía")
                    if template and channel.wa_account_id and channel.whatsapp_number:
                        try:
                            # 1) Crear el mail.message para que aparezca en el chat de Odoo
                            mail_msg = channel.message_post(
                                body=template.body,              # se usa el body de la plantilla
                                message_type='whatsapp_message',  # para indicar que es de WhatsApp
                                subtype_xmlid='mail.mt_comment',
                                author_id=self.env.user.partner_id.id,
                            )

                            # 2) Crear el registro whatsapp.message usando la plantilla completa
                            whatsapp_msg_vals = {
                                'mobile_number': channel.whatsapp_number,
                                'mail_message_id': mail_msg.id,
                                'wa_account_id': channel.wa_account_id.id,
                                'message_type': 'outbound',
                                'state': 'outgoing',
                                'wa_template_id': template.id,  # Esto indica que se enviará como template
                                # Si tu plantilla necesita variables, puedes asignarlas en free_text_json:
                                # 'free_text_json': {'variable1': 'valor1', ...},
                            }
                            whatsapp_msg = self.env['whatsapp.message'].create(whatsapp_msg_vals)

                            # 3) Forzar el envío (o dejar que el cron lo procese)
                            whatsapp_msg._send()

                            # Marcar el canal para no volver a enviar el formulario
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
        return res
