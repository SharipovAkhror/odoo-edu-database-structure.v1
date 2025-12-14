# controllers/onlinepbx_webhook.py
from odoo import http, fields
from odoo.http import request
import logging
import json
from datetime import datetime

_logger = logging.getLogger(__name__)


class OnlinePBXWebhookController(http.Controller):

    @http.route('/onlinepbx/webhook/<string:token>', type='http', auth='public', csrf=False)
    def onlinepbx_webhook(self, token, **kw):
        # ---------------------------------------------------------------------
        #  Check token / settings
        # ---------------------------------------------------------------------
        settings = request.env['onlinepbx.settings'].sudo().search([('token', '=', token)], limit=1)
        if not settings:
            return http.Response("Invalid token", status=403)

        http_req = request.httprequest
        _logger.info(
            "PBX request: method=%s, headers=%s, kw=%s",
            http_req.method,
            dict(http_req.headers),
            kw,
        )

        raw = http_req.data or b""
        _logger.info("Incoming PBX raw bytes: %r", raw)

        text = raw.decode("utf-8", errors="ignore")
        _logger.info("Incoming PBX text decoded: %s", text)

        # payload: kw (form) + optional JSON override
        data = dict(kw) if kw else {}
        if text:
            try:
                json_data = json.loads(text)
                if isinstance(json_data, dict):
                    data = json_data
            except Exception:
                pass

        _logger.info("Incoming PBX payload dict (final): %s", data)

        if not data:
            _logger.warning("OnlinePBX webhook: empty payload, skipping record creation")
            return http.Response("Empty payload", status=200)

        event = data.get("event")

        # ignore call_start if you only want final state
        if event == "call_start":
            _logger.info("OnlinePBX webhook: ignoring call_start for uuid %s", data.get("uuid"))
            return http.Response("Ignored call_start", status=200)

        # ---------------------------------------------------------------------
        #  Start time (unix -> datetime)
        # ---------------------------------------------------------------------
        unix_date = data.get("date")
        start_dt = False
        if unix_date:
            try:
                start_dt = datetime.utcfromtimestamp(int(unix_date))
            except Exception as e:
                _logger.warning("Bad timestamp %r: %s", unix_date, e)
                start_dt = False

        # ---------------------------------------------------------------------
        #  Call state
        # ---------------------------------------------------------------------
        dialog = int(data.get("dialog_duration", 0) or 0)

        if dialog > 0:
            state = "answered"
        elif event == "call_missed":
            state = "missed"
        else:
            state = "not_answered"

        # ---------------------------------------------------------------------
        #  Direction
        # ---------------------------------------------------------------------
        raw_dir = (data.get("direction") or "").lower()
        if raw_dir == "inbound":
            direction = "in"
        elif raw_dir == "outbound":
            direction = "out"
        elif raw_dir == "local":
            direction = "local"
        else:
            direction = "in"

        caller = data.get("caller")
        callee = data.get("callee")
        uuid = data.get("uuid") or "PBX Call"

        # ---------------------------------------------------------------------
        #  Detect extension & match employee
        # ---------------------------------------------------------------------
        ext = False

        # incoming: external -> internal extension
        if direction == "in":
            ext = callee
        # outgoing: internal extension -> external number
        elif direction == "out":
            ext = caller
        # local/internal: pick short-looking number
        elif direction == "local":
            if caller and len(str(caller)) <= 4:
                ext = caller
            elif callee and len(str(callee)) <= 4:
                ext = callee

        if ext:
            ext = str(ext).strip()

        employee = False
        if ext:
            employee = request.env['hr.employee'].sudo().search(
                [('pbx_extension', '=', ext)],
                limit=1,
            )

        # ---------------------------------------------------------------------
        #  Values for onlinepbx.call
        # ---------------------------------------------------------------------
        vals = {
            "name": uuid,
            "direction": direction,
            "state": state,
            "from_number": caller,
            "to_number": callee,
            "external_number": data.get("gateway"),
            "start_time": start_dt,
            "duration_seconds": dialog,
            "recording_url": data.get("download_url"),
            "download_url": data.get("download_url"),
            "has_recording": bool(data.get("download_url")),
            "raw_payload": json.dumps(data, ensure_ascii=False),

            "employee_extension": ext,
            "employee_id": employee.id if employee else False,
        }

        # ---------------------------------------------------------------------
        #  Create / update call
        # ---------------------------------------------------------------------
        Call = request.env["onlinepbx.call"].sudo()
        existing = Call.search([("name", "=", uuid)], limit=1)

        if existing:
            existing.write(vals)
            call = existing
            _logger.info("OnlinePBX webhook: updated call record ID %s for uuid %s", call.id, uuid)
        else:
            call = Call.create(vals)
            _logger.info("OnlinePBX webhook: created call record ID %s for uuid %s", call.id, uuid)

        return http.Response("OK", status=200)
