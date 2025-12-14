from odoo import api, fields, models
import secrets
import logging
import requests
import time
import json
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
import requests


_logger = logging.getLogger(__name__)


class OnlinePBXSettings(models.Model):
    _name = 'onlinepbx.settings'
    _description = 'OnlinePBX Webhook & API Settings'
    _rec_name = 'name'

    name = fields.Char(default="OnlinePBX Settings", required=True)

    # Webhook token
    token = fields.Char(
        string="Webhook Token",
        help="Secret token used in webhook URL",
    )
    webhook_url = fields.Char(
        string="Webhook URL",
        compute="_compute_webhook_url",
        readonly=True,
    )

    # ---- API fields for history sync ----
    api_domain = fields.Char(
        string="API Domain",
        help="Your PBX domain, e.g. pbx123.onpbx.ru",
    )
    api_key = fields.Char(
        string="API Key (key_id:key)",
        help="API key in format key_id:key (see OnlinePBX API page).",
    )
    cdr_path = fields.Char(
        string="CDR Endpoint Path",
        default="/cdr.json",
        help="Relative path to CDR endpoint, e.g. /cdr.json . Adjust to match your OnlinePBX API docs.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('token'):
                vals['token'] = secrets.token_urlsafe(32)
        return super().create(vals_list)

    def write(self, vals):
        # If user clears token, regenerate
        if 'token' in vals and not vals['token']:
            vals['token'] = secrets.token_urlsafe(32)
        return super().write(vals)

    @api.depends('token')
    def _compute_webhook_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.token:
                rec.webhook_url = f"{base_url}/onlinepbx/webhook/{rec.token}"
            else:
                rec.webhook_url = False

    # ======================================================================
    #  ACTION: sync last 7 days call history via OnlinePBX HTTP API
    # ======================================================================

    def action_sync_last_7_days(self):
        """Fetch last 7 days of calls from OnlinePBX HTTP API v2."""
        self.ensure_one()

        if not self.api_domain or not self.api_key:
            raise ValueError("Сначала заполните API Domain и API Key (auth_key) в OnlinePBX Settings.")

        # ---------------------------
        # 1) Получаем key_id:key через /auth.json
        # ---------------------------
        auth_url = f"https://api2.onlinepbx.ru/{self.api_domain}/auth.json"
        auth_payload = {
            "auth_key": self.api_key,  # это тот API-ключ из панели
            "new": "true",
        }

        _logger.info("OnlinePBX sync: POST %s payload=%s", auth_url, auth_payload)

        try:
            auth_resp = requests.post(auth_url, data=auth_payload, timeout=30)
        except Exception as e:
            _logger.exception("OnlinePBX auth error: %s", e)
            raise ValueError(f"HTTP error calling OnlinePBX auth API: {e}")

        if auth_resp.status_code != 200:
            _logger.error("OnlinePBX auth: status %s, body: %s", auth_resp.status_code, auth_resp.text)
            raise ValueError(f"OnlinePBX auth returned {auth_resp.status_code}: {auth_resp.text}")

        try:
            auth_data = auth_resp.json()
        except Exception:
            _logger.exception("OnlinePBX auth: cannot parse JSON: %s", auth_resp.text[:1000])
            raise ValueError("Не удалось распарсить ответ auth.json от OnlinePBX")

        if str(auth_data.get("status")) != "1":
            raise ValueError(f"Авторизация не удалась: {auth_data}")

        key_id = auth_data["data"]["key_id"]
        key = auth_data["data"]["key"]
        api_key_header = f"{key_id}:{key}"

        # ---------------------------
        # 2) Делаем запрос к mongo_history/search.json
        # ---------------------------
        cdr_url = f"https://api2.onlinepbx.ru/{self.api_domain}/mongo_history/search.json"

        now_ts = int(time.time())
        from_ts = now_ts - 7 * 24 * 60 * 60

        payload = {
            "start_stamp_from": from_ts,
            "start_stamp_to": now_ts,
            # сюда можно добавить accountcode, телефоны и т.д. при желании
        }

        headers = {
            "x-pbx-authentication": api_key_header,
            "Accept": "application/json",
        }

        _logger.info("OnlinePBX sync: POST %s payload=%s headers=%s", cdr_url, payload, headers)

        try:
            resp = requests.post(cdr_url, headers=headers, data=payload, timeout=30)
        except Exception as e:
            _logger.exception("OnlinePBX sync: HTTP error: %s", e)
            raise ValueError(f"HTTP error calling OnlinePBX API: {e}")

        if resp.status_code != 200:
            _logger.error("OnlinePBX sync: status %s, body: %s", resp.status_code, resp.text)
            raise ValueError(f"OnlinePBX API returned {resp.status_code}: {resp.text}")

        try:
            data = resp.json()
        except Exception:
            _logger.exception("OnlinePBX sync: parse JSON error: %s", resp.text[:1000])
            raise ValueError("Не удалось распарсить JSON ответ от OnlinePBX")

        # Ответ может быть в разных форматах, берём calls из data
        if isinstance(data, list):
            calls = data
        elif isinstance(data, dict):
            # сначала пытаемся взять data
            inner = data.get("data", data)

            # если внутри снова dict с calls/results
            if isinstance(inner, dict):
                calls = (
                    inner.get("calls")
                    or inner.get("results")
                    or inner.get("items")
                    or []
                )
            else:
                calls = inner or []
        else:
            calls = []

        if not isinstance(calls, list):
            _logger.error("OnlinePBX sync: unexpected format: %s", data)
            raise ValueError("Неожиданный формат ответа mongo_history/search.json")

        _logger.info("OnlinePBX sync: total calls fetched: %s", len(calls))

        Call = self.env['onlinepbx.call'].sudo()
        created = 0
        updated = 0

        for item in calls:
            if not isinstance(item, dict):
                continue

            uuid = item.get("uuid") or item.get("_id")
            if not uuid:
                continue

            call = Call.search([('name', '=', uuid)], limit=1)
            vals = self._prepare_call_vals_from_cdr(item)

            if call:
                call.write(vals)
                updated += 1
            else:
                Call.create(vals)
                created += 1

        _logger.info("OnlinePBX sync done: created=%s, updated=%s", created, updated)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "OnlinePBX Sync",
                "message": f"Created {created} calls, updated {updated} calls (last 7 days).",
                "sticky": False,
            },
        }

    # map ONE HTTP-API call record -> onlinepbx.call
    def _prepare_call_vals_from_cdr(self, item):
        """Map a single CDR record dict to onlinepbx.call vals."""
        start_dt = False
        ts = item.get('start_stamp')
        if ts:
            try:
                start_dt = fields.Datetime.from_timestamp(int(ts))
            except Exception:
                start_dt = False

        billsec = int(item.get("billsec") or 0)

        acc = (item.get("accountcode") or "").lower()
        if acc == "inbound":
            direction = "in"
        elif acc == "outbound":
            direction = "out"
        elif acc == "local":
            direction = "local"
        else:
            direction = "in"

        state = "answered" if billsec > 0 else "not_answered"

        vals = {
            "name": item.get("uuid") or item.get("_id") or "PBX Call",
            "direction": direction,
            "state": state,
            "from_number": item.get("caller_id_number"),
            "to_number": item.get("destination_number"),
            "external_number": item.get("gateway"),
            "start_time": start_dt,
            "duration_seconds": billsec,
            "has_recording": bool(item.get("rec_enabled")),
            # сюда позже можно добавить поля с URL записи, когда найдёшь их в JSON
        }
        return vals
