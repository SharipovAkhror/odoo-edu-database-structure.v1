# -*- coding: utf-8 -*-
"""Async Telegram Message Queue.

The fast API endpoint (turnstile) drops messages here instantly. A cron job
processes the queue every 30 seconds, dispatching to the Telegram Bot API.

This decoupling ensures:
  1. The turnstile never waits for external HTTP calls.
  2. Temporary Telegram outages don't break attendance logging.
  3. Retry logic is handled gracefully (3 attempts, then mark failed).
  4. Full audit trail of all attempted notifications.
"""
import logging
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

# Maximum messages to process per cron run. Prevents runaway loops if a
# large backlog accumulates (e.g. after extended Telegram downtime).
BATCH_SIZE = 100

# Maximum retry attempts before marking a message as permanently failed.
MAX_ATTEMPTS = 3


class TelegramMessageQueue(models.Model):
    _name = 'telegram.message.queue'
    _description = 'Telegram Message Queue'
    _order = 'create_date asc'
    _rec_name = 'event_type'

    # ------------------------------------------------------------------
    # DELIVERY FIELDS
    # ------------------------------------------------------------------
    chat_id = fields.Char(
        string='Chat ID',
        required=True,
        index=True,
        help="Telegram chat_id of the recipient (parent, admin, etc.).",
    )
    message_text = fields.Text(
        string='Message',
        required=True,
        help="Pre-composed message body (HTML format).",
    )
    parse_mode = fields.Selection(
        selection=[
            ('HTML', 'HTML'),
            ('Markdown', 'Markdown'),
        ],
        string='Parse Mode',
        default='HTML',
    )

    # ------------------------------------------------------------------
    # STATE MACHINE
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
        ],
        string='Status',
        default='pending',
        required=True,
        index=True,
    )
    attempt_count = fields.Integer(
        string='Attempts',
        default=0,
        help="Number of send attempts made so far.",
    )
    max_attempts = fields.Integer(
        string='Max Attempts',
        default=MAX_ATTEMPTS,
    )
    error_message = fields.Text(
        string='Last Error',
        help="Error message from the most recent failed attempt.",
    )
    sent_datetime = fields.Datetime(
        string='Sent At',
        readonly=True,
    )
    next_retry_after = fields.Datetime(
        string='Next Retry After',
        help="Do not retry before this time (exponential backoff).",
    )

    # ------------------------------------------------------------------
    # SOURCE TRACING
    # ------------------------------------------------------------------
    event_id = fields.Many2one(
        'edu.faceid.event',
        string='Source Event',
        ondelete='set null',
        index=True,
        help="The FaceID event that triggered this notification.",
    )
    event_type = fields.Selection(
        selection=[
            ('student_entered', 'Student Entered'),
            ('student_left', 'Student Left'),
            ('balance_warning', 'Balance Warning'),
            ('no_class_alert', 'No Scheduled Class'),
            ('system_alert', 'System Alert'),
        ],
        string='Event Type',
        index=True,
    )
    student_id = fields.Many2one(
        'res.partner',
        string='Student',
        ondelete='set null',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    # ==================================================================
    # QUEUE PROCESSOR (called by cron)
    # ==================================================================
    @api.model
    def _process_queue(self):
        """Process pending messages in the Telegram queue.

        Called by the scheduled cron job every 30 seconds. Processes up to
        BATCH_SIZE messages per run with exponential backoff on failures.

        Flow:
          1. Fetch pending messages that are eligible for retry.
          2. For each: attempt send via telegram.bot.config.send_message().
          3. On success: mark 'sent', record timestamp.
          4. On failure: increment attempt_count, apply backoff. If exhausted
             (attempt_count >= max_attempts), mark 'failed' permanently.
        """
        from .telegram_config import TelegramSendError

        now = fields.Datetime.now()

        # Find eligible messages: pending, with retry time passed (or no retry set)
        domain = [
            ('state', '=', 'pending'),
            '|',
            ('next_retry_after', '=', False),
            ('next_retry_after', '<=', now),
        ]
        messages = self.search(domain, limit=BATCH_SIZE, order='create_date asc')

        if not messages:
            return

        _logger.info(
            "Telegram queue: processing %d pending messages", len(messages)
        )

        # Group by company for config lookup efficiency
        by_company = {}
        for msg in messages:
            by_company.setdefault(msg.company_id.id, self.env['telegram.message.queue'])
            by_company[msg.company_id.id] |= msg

        for company_id, company_messages in by_company.items():
            config = self.env['telegram.bot.config'].sudo().search([
                ('company_id', '=', company_id),
                ('is_active', '=', True),
            ], limit=1)

            if not config:
                _logger.warning(
                    "Telegram queue: no active bot config for company %d. "
                    "Skipping %d messages.", company_id, len(company_messages)
                )
                continue

            for msg in company_messages:
                self._send_single_message(msg, config, now)

        _logger.info("Telegram queue: processing complete")

    def _send_single_message(self, msg, config, now):
        """Attempt to send a single queued message.

        Args:
            msg: telegram.message.queue record
            config: telegram.bot.config record
            now: current datetime for timestamps
        """
        from .telegram_config import TelegramSendError

        try:
            config.send_message(
                chat_id=msg.chat_id,
                text=msg.message_text,
                parse_mode=msg.parse_mode or 'HTML',
            )
            msg.write({
                'state': 'sent',
                'sent_datetime': now,
                'error_message': False,
            })
        except TelegramSendError as e:
            new_attempt_count = msg.attempt_count + 1
            error_text = str(e)

            if new_attempt_count >= msg.max_attempts:
                # Exhausted retries — mark as permanently failed
                msg.write({
                    'state': 'failed',
                    'attempt_count': new_attempt_count,
                    'error_message': error_text,
                })
                _logger.warning(
                    "Telegram queue: message %d permanently failed after %d "
                    "attempts. chat_id=%s error=%s",
                    msg.id, new_attempt_count, msg.chat_id, error_text,
                )
                # Update failed counter on config
                config.sudo().write({
                    'messages_failed': config.messages_failed + 1,
                })
            else:
                # Apply exponential backoff: 30s, 90s, 270s (30 * 3^attempt)
                backoff_seconds = 30 * (3 ** (new_attempt_count - 1))
                retry_after = now + timedelta(seconds=backoff_seconds)
                msg.write({
                    'attempt_count': new_attempt_count,
                    'error_message': error_text,
                    'next_retry_after': retry_after,
                })
                _logger.info(
                    "Telegram queue: message %d attempt %d/%d failed. "
                    "Retry after %s. error=%s",
                    msg.id, new_attempt_count, msg.max_attempts,
                    retry_after, error_text,
                )
        except Exception as e:
            # Catch-all for unexpected errors (don't crash the cron)
            msg.write({
                'attempt_count': msg.attempt_count + 1,
                'error_message': "Unexpected: %s" % str(e),
            })
            _logger.exception(
                "Telegram queue: unexpected error processing message %d", msg.id
            )

    # ==================================================================
    # MAINTENANCE
    # ==================================================================
    @api.model
    def _cleanup_old_messages(self):
        """Delete successfully sent messages older than 30 days.

        Called by a weekly cron to prevent unbounded table growth.
        Failed messages are kept indefinitely for debugging.
        """
        cutoff = fields.Datetime.now() - timedelta(days=30)
        old_sent = self.search([
            ('state', '=', 'sent'),
            ('sent_datetime', '<', cutoff),
        ])
        count = len(old_sent)
        if old_sent:
            old_sent.unlink()
            _logger.info("Telegram queue cleanup: deleted %d old sent messages", count)

    # ==================================================================
    # HELPER: ENQUEUE
    # ==================================================================
    @api.model
    def enqueue(self, chat_id, message_text, event_id=False, event_type=False,
                student_id=False, parse_mode='HTML'):
        """Create a new pending message in the queue.

        This is the primary entry point used by the FaceID API controller.
        It is intentionally fast (single create, no external calls).

        Args:
            chat_id (str): Recipient Telegram chat ID.
            message_text (str): Pre-composed message body.
            event_id (int): Optional linked edu.faceid.event ID.
            event_type (str): Optional event type classification.
            student_id (int): Optional linked student res.partner ID.
            parse_mode (str): 'HTML' or 'Markdown'.

        Returns:
            telegram.message.queue: The created queue record.
        """
        if not chat_id or not message_text:
            _logger.debug(
                "Telegram enqueue skipped: no chat_id or empty message. "
                "chat_id=%s student_id=%s event_type=%s",
                chat_id, student_id, event_type,
            )
            return self.browse()

        return self.create({
            'chat_id': str(chat_id),
            'message_text': message_text,
            'parse_mode': parse_mode,
            'event_id': event_id,
            'event_type': event_type,
            'student_id': student_id,
            'company_id': self.env.company.id,
        })
