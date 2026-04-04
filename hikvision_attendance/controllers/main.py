# -*- coding: utf-8 -*-
import logging
import re
from datetime import datetime, timezone

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class HikvisionAttendanceController(http.Controller):

    @http.route(
        "/hikvision/attendance",
        type="http",
        auth="public",
        methods=["POST", "GET", "OPTIONS"],
        csrf=False,
    )
    def hikvision_attendance(self, **kwargs):
        """
        Hikvision "HTTP Listening" / webhook receiver.

        - GET  : returns 200 OK (useful for testing and some device probes)
        - POST : accepts raw payload (often XML or multipart), logs it, and creates attendance
        - OPTIONS : returns 200 OK (CORS / preflight friendly, harmless)
        """

        method = request.httprequest.method

        # Quick health check / probe support
        if method in ("GET", "OPTIONS"):
            return request.make_response("OK", status=200, headers=[("Content-Type", "text/plain")])

        # POST handling
        raw_bytes = request.httprequest.get_data() or b""
        # Keep both decoded text (best effort) and bytes
        raw_text = ""
        try:
            raw_text = raw_bytes.decode("utf-8", errors="ignore")
        except Exception:
            raw_text = str(raw_bytes)

        headers = dict(request.httprequest.headers)

        # Always log at least the start of the payload so we can learn the real format
        _logger.warning(
            "Hikvision webhook HIT: path=%s headers=%s raw_preview=%s",
            request.httprequest.path,
            headers,
            raw_text[:4000],
        )

        # --- Very forgiving extraction (refine after you see real payload) ---
        candidate_keys = [
            r"<employeeNo>(.*?)</employeeNo>",
            r"<employeeNoString>(.*?)</employeeNoString>",
            r"\"employeeNo\"\s*:\s*\"(.*?)\"",
            r"\"employeeNoString\"\s*:\s*\"(.*?)\"",
            r"<cardNo>(.*?)</cardNo>",
            r"\"cardNo\"\s*:\s*\"(.*?)\"",
            r"<personId>(.*?)</personId>",
            r"\"personId\"\s*:\s*\"(.*?)\"",
            r"<userID>(.*?)</userID>",
            r"\"userID\"\s*:\s*\"(.*?)\"",
        ]

        person_code = None
        for pat in candidate_keys:
            m = re.search(pat, raw_text, flags=re.IGNORECASE | re.DOTALL)
            if m and m.group(1):
                person_code = m.group(1).strip()
                break

        # Timestamp: later we can parse device time from payload.
        event_dt = datetime.now(timezone.utc)

        # --- Map device person_code to Odoo employee ---
        # Recommended: store device ID/card number in hr.employee.barcode
        employee = None
        if person_code:
            employee = request.env["hr.employee"].sudo().search([("barcode", "=", person_code)], limit=1)

        if not employee:
            # Keep it 200 so the device doesn't keep retrying forever.
            _logger.warning(
                "Hikvision: No employee match. person_code=%s raw_preview=%s",
                person_code,
                raw_text[:4000],
            )
            return request.make_response("OK", status=200, headers=[("Content-Type", "text/plain")])

        # --- Create/Toggle attendance ---
        Attendance = request.env["hr.attendance"].sudo()
        open_att = Attendance.search(
            [
                ("employee_id", "=", employee.id),
                ("check_out", "=", False),
            ],
            limit=1,
            order="check_in desc",
        )

        if open_att:
            open_att.write({"check_out": event_dt})
            _logger.warning("Hikvision: check_out employee=%s (%s) at %s", employee.name, employee.id, event_dt)
        else:
            Attendance.create({"employee_id": employee.id, "check_in": event_dt})
            _logger.warning("Hikvision: check_in employee=%s (%s) at %s", employee.name, employee.id, event_dt)

        return request.make_response("OK", status=200, headers=[("Content-Type", "text/plain")])
