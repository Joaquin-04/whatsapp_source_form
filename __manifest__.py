# -*- coding: utf-8 -*-
{
    'name': "WhatsApp Source Form",
    'summary': "Envía un formulario interactivo para capturar la fuente del lead en chats de WhatsApp",
    'description': """
        Este módulo extiende la integración de WhatsApp en Odoo 17 para enviar automáticamente un mensaje interactivo
        (basado en una plantilla preaprobada) al recibir un nuevo chat. El mensaje contiene opciones como:
          - Google o YouTube
          - Facebook o Instagram
          - Landing Page
        La respuesta del usuario se captura y se almacena para luego integrarla en la creación del lead.
        
        Se aprovecha la configuración y conexión ya existente del módulo WhatsApp (Odoo WhatsApp Integration)
        y se utiliza la plantilla interactiva (por ejemplo, 'formulario') sincronizada desde Meta.
    """,
    'author': "Tu Nombre",
    'website': "https://www.tuempresa.com",
    'category': 'WhatsApp',
    'version': '1.0',
    'depends': [
        'whatsapp',              # Módulo de Odoo WhatsApp Integration
        'whatsapp_extra_menu',   # Módulo que usas para crear leads desde el chat
    ],
    'data': [
        # Si es necesario agregar vistas, acciones u otros datos, se pueden incluir aquí.
    ],
    'installable': True,
    'application': False,
}
