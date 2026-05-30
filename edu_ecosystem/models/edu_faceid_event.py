# -*- coding: utf-8 -*-
"""FaceID Event Log — permanent record of every turnstile event.

Every scan creates a record here regardless of whether the student exists,
has a class, or has a positive balance. This serves as:
  - Audit trail (who entered the building, when)
  - Debugging (turnstile payload issues)
  - Analytics (peak hours, traffic patterns)
  - Future: backfill edu.attendance.line from events

The teacher remains the final authority on class attendance. This model
does NOT modify edu.attendance.line — it only logs the physical event.
"""
import logging
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class EduFaceidEvent(models.Model):
    _name = 'edu.faceid.event'
    _description = 'Turnstile FaceID Event (Raw Log)'
    _order = 'event_datetime desc, id desc'
    _rec_name = 'display_name'

    # ------------------------------------------------------------------
    # EVENT DATA
    # ------------------------------------------------------------------
    student_id = fields.Many2one(
        'res.partner',
        string='Student',
        ondelete='set null',
        index=True,
        help="Matched student. Empty if the barcode didn't match anyone.",
    )
    student_code = fields.Char(
        string='Student Code (Barcode)',
        required=True,
        index=True,
        help="Raw barcode/faceID code received from the turnstile device.",
    )
    student_name = fields.Char(
        string='Student Name',
        compute='_compute_student_name',
        store=True,
    )
    device_id = fields.Char(
        string='Device ID',
        index=True,
        help="Identifier of the turnstile device that reported this event.",
    )
    direction = fields.Selection(
        selection=[
            ('in', 'Entry'),
            ('out', 'Exit'),
        ],
        string='Direction',
        default='in',
        index=True,
    )
    event_datetime = fields.Datetime(
        string='Event Time',
        required=True,
        default=fields.Datetime.now,
        index=True,
        help="When the student was identified by the turnstile.",
    )

    # ------------------------------------------------------------------
    # SCHEDULE CONTEXT (snapshot at event time)
    # ------------------------------------------------------------------
    has_class_now = fields.Boolean(
        string='Has Class',
        default=False,
        help="Whether the student had a scheduled class at the time of entry.",
    )
    timetable_id = fields.Many2one(
        'edu.timetable',
        string='Matched Timetable',
        ondelete='set null',
        help="The timetable entry that was active at the time of this event.",
    )
    group_id = fields.Many2one(
        'edu.group',
        string='Group',
        related='timetable_id.group_id',
        store=True,
        readonly=True,
    )

    # ------------------------------------------------------------------
    # FINANCIAL CONTEXT (snapshot at event time)
    # ------------------------------------------------------------------
    balance_ok = fields.Boolean(
        string='Balance OK',
        default=True,
        help="Whether the student had a positive finance_balance at event time.",
    )
    finance_balance_snapshot = fields.Float(
        string='Balance at Event Time',
        readonly=True,
        help="Snapshot of the student's finance_balance when this event was logged.",
    )

    # ------------------------------------------------------------------
    # PROCESSING STATE
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[
            ('logged', 'Logged'),
            ('processed', 'Attendance Recorded'),
            ('ignored', 'Ignored (No Class)'),
            ('unmatched', 'Unmatched (Unknown Code)'),
        ],
        string='Status',
        default='logged',
        required=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # NOTIFICATION TRACKING
    # ------------------------------------------------------------------
    notification_sent = fields.Boolean(
        string='Notification Sent',
        default=False,
        help="Whether a Telegram notification was queued for this event.",
    )
    telegram_queue_id = fields.Many2one(
        'telegram.message.queue',
        string='Telegram Message',
        ondelete='set null',
    )

    # ------------------------------------------------------------------
    # METADATA
    # ------------------------------------------------------------------
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    raw_payload = fields.Text(
        string='Raw Payload',
        help="Original request body from the turnstile (for debugging).",
    )
    response_payload = fields.Text(
        string='Response Sent',
        help="JSON response returned to the turnstile.",
    )
    processing_time_ms = fields.Integer(
        string='Processing Time (ms)',
        help="How long the endpoint took to respond (milliseconds).",
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name_custom',
        store=True,
    )

    # ==================================================================
    # COMPUTES
    # ==================================================================
    @api.depends('student_id', 'student_id.name')
    def _compute_student_name(self):
        for rec in self:
            rec.student_name = rec.student_id.name if rec.student_id else ''

    @api.depends('student_name', 'student_code', 'event_datetime', 'direction')
    def _compute_display_name_custom(self):
        for rec in self:
            name = rec.student_name or rec.student_code or 'Unknown'
            direction_label = dict(
                self._fields['direction'].selection
            ).get(rec.direction, '')
            dt_str = fields.Datetime.to_string(rec.event_datetime) if rec.event_datetime else ''
            rec.display_name = "%s [%s] %s" % (name, direction_label, dt_str)

    # ==================================================================
    # BUSINESS LOGIC: SCHEDULE + BALANCE CHECKS
    # ==================================================================
    @api.model
    def check_student_schedule(self, student, event_dt):
        """Check if the student has a scheduled class right now.

        Uses indexed timetable fields with a +-15 minute buffer to accommodate
        early/late arrivals. Returns the first matching timetable entry.

        Args:
            student (res.partner): The student record.
            event_dt (datetime): The event timestamp.

        Returns:
            tuple: (has_class: bool, timetable: edu.timetable or False)
        """
        # Get all active group IDs for this student
        active_enrollments = self.env['edu.group.student'].sudo().search([
            ('student_id', '=', student.id),
            ('state', '=', 'active'),
        ])
        group_ids = active_enrollments.mapped('group_id').ids

        if not group_ids:
            return False, False

        # Search for a timetable entry happening NOW (+/- 15 min buffer)
        buffer = timedelta(minutes=15)
        timetable = self.env['edu.timetable'].sudo().search([
            ('group_id', 'in', group_ids),
            ('start_datetime', '<=', event_dt + buffer),
            ('end_datetime', '>=', event_dt - buffer),
            ('state', 'in', ['scheduled', 'in_progress']),
        ], limit=1, order='start_datetime asc')

        return bool(timetable), timetable or False

    @api.model
    def check_student_balance(self, student):
        """Check if the student's financial situation is OK.

        A student is considered "balance OK" if:
          1. They have at least one active (non-frozen) enrollment, AND
          2. Their finance_balance is >= 0 (not in debt).

        We do NOT block entry based on balance (soft signal only). The actual
        freeze logic is handled by the attendance confirmation workflow.

        Args:
            student (res.partner): The student record.

        Returns:
            tuple: (balance_ok: bool, balance_amount: float)
        """
        balance = student.finance_balance or 0.0
        has_active = bool(
            self.env['edu.group.student'].sudo().search_count([
                ('student_id', '=', student.id),
                ('state', '=', 'active'),
            ])
        )
        # Balance is OK if student has active enrollment and non-negative balance
        balance_ok = has_active and balance >= 0.0
        return balance_ok, balance

    # ==================================================================
    # NOTIFICATION COMPOSER
    # ==================================================================
    def _compose_notification(self):
        """Compose a Telegram notification message for this event.

        Returns:
            tuple: (chat_id: str or False, message_text: str, event_type: str)
        """
        self.ensure_one()

        # Recipient is the student's parent
        chat_id = False
        if self.student_id:
            chat_id = self.student_id.parent_telegram_chat_id

        if not chat_id:
            return False, '', ''

        student_name = self.student_name or self.student_code

        if self.direction == 'out':
            message = _(
                "<b>%(name)s</b> chiqdi.\n"
                "Vaqt: %(time)s",
                name=student_name,
                time=fields.Datetime.context_timestamp(
                    self, self.event_datetime
                ).strftime('%H:%M') if self.event_datetime else '?',
            )
            return chat_id, message, 'student_left'

        # Direction = 'in' (entry)
        time_str = fields.Datetime.context_timestamp(
            self, self.event_datetime
        ).strftime('%H:%M') if self.event_datetime else '?'

        if self.has_class_now and self.timetable_id:
            group_name = self.timetable_id.group_id.name or ''
            lesson_start = ''
            lesson_end = ''
            if self.timetable_id.start_datetime:
                lesson_start = fields.Datetime.context_timestamp(
                    self, self.timetable_id.start_datetime
                ).strftime('%H:%M')
            if self.timetable_id.end_datetime:
                lesson_end = fields.Datetime.context_timestamp(
                    self, self.timetable_id.end_datetime
                ).strftime('%H:%M')

            message = _(
                "<b>%(name)s</b> kirdi.\n"
                "Dars: %(group)s (%(start)s-%(end)s)\n"
                "Vaqt: %(time)s",
                name=student_name,
                group=group_name,
                start=lesson_start,
                end=lesson_end,
                time=time_str,
            )
            event_type = 'student_entered'

            # Add balance warning if applicable
            if not self.balance_ok:
                message += _(
                    "\n<i>Balans: %(balance)s (to'lov kutilmoqda)</i>",
                    balance="{:,.0f}".format(self.finance_balance_snapshot),
                )
                event_type = 'balance_warning'

            return chat_id, message, event_type

        else:
            # No class right now
            message = _(
                "<b>%(name)s</b> kirdi.\n"
                "Bugun dars yo'q.\n"
                "Vaqt: %(time)s",
                name=student_name,
                time=time_str,
            )
            return chat_id, message, 'no_class_alert'

    def _enqueue_notification(self):
        """Compose and enqueue the Telegram notification for this event.

        Called by the API controller after creating the event record.
        Fire-and-forget: errors here do NOT affect the API response.
        """
        self.ensure_one()
        try:
            chat_id, message_text, event_type = self._compose_notification()
            if chat_id and message_text:
                queue_record = self.env['telegram.message.queue'].sudo().enqueue(
                    chat_id=chat_id,
                    message_text=message_text,
                    event_id=self.id,
                    event_type=event_type,
                    student_id=self.student_id.id if self.student_id else False,
                )
                if queue_record:
                    self.write({
                        'notification_sent': True,
                        'telegram_queue_id': queue_record.id,
                    })
        except Exception as e:
            # Never crash the API endpoint for a notification failure
            _logger.warning(
                "Failed to enqueue Telegram notification for event %d: %s",
                self.id, str(e),
            )
