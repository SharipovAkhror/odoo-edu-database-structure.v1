# -*- coding: utf-8 -*-
"""Extend res.partner with Telegram notification fields.

Adds the parent's Telegram chat_id so the ecosystem can send entry/exit
notifications when a student is identified by the turnstile.
"""
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    parent_telegram_chat_id = fields.Char(
        string='Parent Telegram Chat ID',
        help="Telegram chat_id of the student's parent or guardian. "
             "Used to send entry/exit notifications from the turnstile system. "
             "Obtain by having the parent message the bot and using /start.",
    )

    telegram_notifications_enabled = fields.Boolean(
        string='Telegram Notifications',
        default=True,
        help="When enabled, entry/exit notifications are sent to the parent's "
             "Telegram account. Disable to stop notifications for this student.",
    )

    # Count of FaceID events for this student (for smart buttons in UI later)
    faceid_event_count = fields.Integer(
        string='FaceID Events',
        compute='_compute_faceid_event_count',
        store=False,
    )

    def _compute_faceid_event_count(self):
        Event = self.env['edu.faceid.event']
        for partner in self:
            if partner.is_student:
                partner.faceid_event_count = Event.search_count([
                    ('student_id', '=', partner.id),
                ])
            else:
                partner.faceid_event_count = 0
