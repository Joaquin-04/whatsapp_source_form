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
        res = super(DiscussChannel, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        # Procesar mensaje entrante de WhatsApp

        # Solo pa testear
        self.formulario_sent = False


        if self.channel_type == 'whatsapp' and not self.formulario_sent:
            template = self.env['whatsapp.template'].search([('template_name', '=', 'formulario')], limit=1)
            if template:
                try:
                    self._send_whatsapp_template(template)
                    self.formulario_sent = True
                except Exception as e:
                    _logger.error(f"Error enviando plantilla: {str(e)}")
        # Capturar respuesta del botón
        if msg_vals and 'interactive' in msg_vals:
            button_reply = msg_vals['interactive'].get('button_reply')
            if button_reply:
                self._process_button_response(button_reply.get('title'))
        return res

    def _send_whatsapp_template(self, template):
        """Envía la plantilla de WhatsApp y vincula al canal."""
        _logger.warning(f"whatsapp_number: {self.whatsapp_number}")
        _logger.warning(f"self.wa_account_id.id: {self.wa_account_id.id}")
        _logger.warning(f"template.id: {template.id}")

        try:
            # Crear mail.message primero para vincular
            mail_message = self.env['mail.message'].create({
                'model': 'discuss.channel',
                'res_id': self.id,
                'body': 'Enviando plantilla formulario',
            })

            # Crear whatsapp.message con todos los campos requeridos
            whatsapp_msg = self.env['whatsapp.message'].create({
                'mobile_number': self.whatsapp_number,
                'wa_template_id': template.id,
                'wa_account_id': self.wa_account_id.id,
                'message_type': 'template',  # Obligatorio para plantillas
                'free_text_json': {},  # JSON vacío si no hay variables
                'mail_message_id': mail_message.id,  # Vincular a mail.message
            })
            _logger.warning("WhatsApp message creado: %s", whatsapp_msg.id)
            
            whatsapp_msg._send()
            _logger.warning("Plantilla enviada correctamente")
        except Exception as e:
            _logger.error("Error al enviar plantilla: %s", str(e))
            raise

        
    def _process_button_response(self, button_title):
        """Mapea la respuesta del botón al campo source_option."""
        mapping = {
            'Google o YouTube': 'google',
            'Facebook o Instagram': 'social',
            'Landing Page': 'landing',
        }
        self.source_option = mapping.get(button_title)