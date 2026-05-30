# -*- coding: utf-8 -*-
"""Telegram Bot Configuration.

Stores the bot token and provides helper methods for sending messages.
Actual dispatch is handled by the queue processor (telegram.message.queue),
not called inline during the fast API endpoint.
"""
import json
import logging
import urllib.request
import urllib.error
import urllib.parse

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Telegram Bot API base URL
TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"

# Timeout for Telegram API calls (seconds). Must be short enough that the
# cron doesn't stack up, but long enough for normal API latency.
TELEGRAM_TIMEOUT = 10


class TelegramBotConfig(models.Model):
    """Singleton-style configuration for the Telegram bot.

    One record per company. Stores the bot token and default admin chat ID.
    Provides low-level send methods used by the queue processor.
    """
    _name = 'telegram.bot.config'
    _description = 'Telegram Bot Configuration'
    _rec_name = 'bot_name'

    bot_name = fields.Char(
        string='Bot Name',
        required=True,
        help="Human-readable label for this bot (e.g. 'UStudy Attendance Bot').",
    )
    bot_token = fields.Char(
        string='Bot Token',
        required=True,
        help="Token from @BotFather (e.g. 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11).",
    )
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help="When disabled, the queue processor skips all messages for this bot.",
    )
    default_admin_chat_id = fields.Char(
        string='Admin Chat ID',
        help="Default Telegram chat_id for system alerts and errors.",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    # Statistics
    messages_sent = fields.Integer(
        string='Messages Sent',
        readonly=True,
        default=0,
    )
    messages_failed = fields.Integer(
        string='Messages Failed',
        readonly=True,
        default=0,
    )
    last_send_datetime = fields.Datetime(
        string='Last Send',
        readonly=True,
    )

    _sql_constraints = [
        ('company_unique', 'unique(company_id)',
         'Only one Telegram bot configuration per company is allowed.'),
    ]

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------
    @api.model
    def get_config(self):
        """Retrieve the active Telegram bot config for the current company.

        Returns:
            telegram.bot.config record or empty recordset if not configured.
        """
        config = self.search([
            ('company_id', '=', self.env.company.id),
            ('is_active', '=', True),
        ], limit=1)
        return config

    def send_message(self, chat_id, text, parse_mode='HTML'):
        """Send a single message via the Telegram Bot API.

        This is the low-level transport method. It should ONLY be called by
        the queue processor cron, never by the fast API endpoint.

        Args:
            chat_id (str): Telegram chat_id of the recipient.
            text (str): Message body (supports HTML or Markdown).
            parse_mode (str): 'HTML' or 'Markdown' (default: HTML).

        Returns:
            dict: The Telegram API response (parsed JSON).

        Raises:
            TelegramSendError: If the API returns a non-OK response.
        """
        self.ensure_one()
        if not self.bot_token:
            raise UserError(_("Telegram bot token is not configured."))
        if not chat_id:
            raise UserError(_("No chat_id provided for Telegram message."))

        url = "{base}/sendMessage".format(
            base=TELEGRAM_API_BASE.format(token=self.bot_token)
        )
        payload = {
            'chat_id': str(chat_id),
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True,
        }
        data = json.dumps(payload).encode('utf-8')
        headers = {'Content-Type': 'application/json'}

        req = urllib.request.Request(url, data=data, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req, timeout=TELEGRAM_TIMEOUT) as response:
                response_body = response.read().decode('utf-8')
                result = json.loads(response_body)
                if not result.get('ok'):
                    error_desc = result.get('description', 'Unknown Telegram error')
                    _logger.warning(
                        "Telegram API error: chat_id=%s error=%s",
                        chat_id, error_desc,
                    )
                    raise TelegramSendError(error_desc)
                # Update stats
                self.sudo().write({
                    'messages_sent': self.messages_sent + 1,
                    'last_send_datetime': fields.Datetime.now(),
                })
                return result
        except urllib.error.HTTPError as e:
            error_body = ''
            try:
                error_body = e.read().decode('utf-8', errors='ignore')
            except Exception:
                pass
            _logger.warning(
                "Telegram HTTP error: chat_id=%s status=%s body=%s",
                chat_id, e.code, error_body[:500],
            )
            raise TelegramSendError(
                "HTTP %s: %s" % (e.code, error_body[:200])
            )
        except urllib.error.URLError as e:
            _logger.warning(
                "Telegram URL error: chat_id=%s reason=%s",
                chat_id, str(e.reason),
            )
            raise TelegramSendError("Connection error: %s" % str(e.reason))
        except Exception as e:
            _logger.exception("Telegram unexpected error: chat_id=%s", chat_id)
            raise TelegramSendError("Unexpected: %s" % str(e))

    def action_test_connection(self):
        """Test the bot token by calling getMe."""
        self.ensure_one()
        url = "{base}/getMe".format(
            base=TELEGRAM_API_BASE.format(token=self.bot_token)
        )
        req = urllib.request.Request(url, method='GET')
        try:
            with urllib.request.urlopen(req, timeout=TELEGRAM_TIMEOUT) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('ok'):
                    bot_info = result.get('result', {})
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _(
                                "Connection successful. Bot: @%(username)s (%(name)s)",
                                username=bot_info.get('username', '?'),
                                name=bot_info.get('first_name', '?'),
                            ),
                            'type': 'success',
                            'sticky': False,
                        },
                    }
                raise UserError(_("Bot token is invalid: %s") % result.get('description', ''))
        except urllib.error.URLError as e:
            raise UserError(_(
                "Cannot connect to Telegram API: %s"
            ) % str(e.reason))

    def action_send_test_message(self):
        """Send a test message to the admin chat."""
        self.ensure_one()
        if not self.default_admin_chat_id:
            raise UserError(_("Please set the Admin Chat ID first."))
        self.send_message(
            self.default_admin_chat_id,
            "<b>UStudy Ecosystem</b>\nTest message sent successfully.",
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _("Test message sent to admin chat."),
                'type': 'success',
                'sticky': False,
            },
        }


class TelegramSendError(Exception):
    """Raised when a Telegram API call fails.

    Not a UserError because it's caught by the queue processor for retry
    logic. It should never bubble up to the end user.
    """
    pass
