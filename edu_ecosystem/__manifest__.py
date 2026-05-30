# -*- coding: utf-8 -*-
{
    'name': 'Education Ecosystem (FaceID + Telegram)',
    'version': '19.0.1.0.0',
    'category': 'Education',
    'summary': 'Turnstile FaceID attendance API + async Telegram notifications',
    'author': 'Ustudy',
    'license': 'LGPL-3',
    'description': """
Education Ecosystem — Block C: FaceID & Telegram MVP
=====================================================
* Fast JSON API endpoint for Hikvision turnstile FaceID events
* Raw event logging (edu.faceid.event) for audit + analytics
* Schedule-aware class detection (uses Block A edu.group.schedule)
* Balance-aware status reporting (uses Block B finance_balance)
* Async Telegram message queue with cron-based dispatch
* Fire-and-forget pattern: turnstile never waits for external calls
    """,
    'depends': [
        'base',
        'mail',
        'ustudy_group',
        'edu_finance',
    ],
    'data': [
        # Security
        'security/ecosystem_groups.xml',
        'security/ir.model.access.csv',
        # Data
        'data/config_data.xml',
        'data/cron_data.xml',
        # Views
        'views/edu_faceid_event_views.xml',
        'views/telegram_message_queue_views.xml',
        'views/telegram_bot_config_views.xml',
        'views/res_partner_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
