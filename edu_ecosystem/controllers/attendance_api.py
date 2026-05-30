# -*- coding: utf-8 -*-
"""Fast JSON API endpoint for turnstile FaceID attendance events.

Endpoint: POST /api/attendance/faceid

Design constraints:
  - Sub-100ms response time (no external HTTP calls in the request path).
  - auth="none" with manual API key check (no session overhead).
  - csrf=False (machine-to-machine communication).
  - Fire-and-forget Telegram notifications via queue (async).
  - Always returns 200 (turnstiles retry on non-200, causing duplicates).

Expected request:
    POST /api/attendance/faceid
    Content-Type: application/json
    X-Api-Key: <shared secret>

    {
        "student_code": "12345",
        "device_id": "TURNSTILE_01",
        "timestamp": "2025-01-15T14:02:00Z",  (optional)
        "direction": "in"                      (optional, default "in")
    }

Response (always 200):
    {
        "status": "ok" | "warning" | "error",
        "student_name": "...",
        "has_class_now": true/false,
        "group_name": "..." or null,
        "balance_ok": true/false,
        "event_id": 42,
        "message": "..."  (only on warning/error)
    }
"""
import json
import logging
import time
from datetime import datetime, timezone

from odoo import http, fields as odoo_fields
from odoo.http import request

_logger = logging.getLogger(__name__)

# ir.config_parameter key for the shared API secret
API_KEY_PARAM = 'edu_ecosystem.faceid_api_key'


class FaceIDAttendanceController(http.Controller):

    @http.route(
        '/api/attendance/faceid',
        type='http',
        auth='none',
        methods=['POST', 'GET', 'OPTIONS'],
        csrf=False,
        save_session=False,
    )
    def faceid_attendance(self, **kwargs):
        """Main FaceID attendance endpoint.

        GET/OPTIONS: health check (returns 200 OK).
        POST: process a FaceID event.
        """
        method = request.httprequest.method

        # Health check / CORS preflight
        if method in ('GET', 'OPTIONS'):
            return self._json_response({'status': 'ok', 'message': 'FaceID API active'})

        # Start timing for performance tracking
        start_time = time.time()

        # --- Parse request body ---
        try:
            body = request.httprequest.get_data(as_text=True)
            data = json.loads(body) if body else {}
        except (json.JSONDecodeError, ValueError) as e:
            _logger.warning("FaceID API: invalid JSON body: %s", str(e))
            return self._json_response({
                'status': 'error',
                'message': 'Invalid JSON request body',
            })

        # --- Authenticate via API key ---
        auth_error = self._check_api_key()
        if auth_error:
            return auth_error

        # --- Extract fields ---
        student_code = data.get('student_code', '').strip()
        device_id = data.get('device_id', '').strip()
        direction = data.get('direction', 'in').strip().lower()
        timestamp_str = data.get('timestamp', '').strip()

        if not student_code:
            return self._json_response({
                'status': 'error',
                'message': 'Missing required field: student_code',
            })

        # Parse timestamp (fallback to server time)
        event_dt = self._parse_timestamp(timestamp_str)

        # Validate direction
        if direction not in ('in', 'out'):
            direction = 'in'

        # --- Establish environment (sudo for performance, no ACL checks) ---
        env = request.env(su=True)

        # --- Lookup student by barcode ---
        student = env['res.partner'].search([
            ('barcode', '=', student_code),
            ('is_student', '=', True),
        ], limit=1)

        if not student:
            # Log unmatched event for debugging
            event = self._create_event(env, {
                'student_code': student_code,
                'device_id': device_id,
                'direction': direction,
                'event_datetime': event_dt,
                'state': 'unmatched',
                'has_class_now': False,
                'balance_ok': False,
                'raw_payload': body,
            })
            elapsed_ms = int((time.time() - start_time) * 1000)
            event.write({'processing_time_ms': elapsed_ms})
            return self._json_response({
                'status': 'warning',
                'student_name': None,
                'has_class_now': False,
                'group_name': None,
                'balance_ok': False,
                'event_id': event.id,
                'message': 'Unknown student code: %s' % student_code,
            })

        # --- Schedule check (Block A integration) ---
        Event = env['edu.faceid.event']
        has_class, timetable = Event.check_student_schedule(student, event_dt)

        # --- Balance check (Block B integration) ---
        balance_ok, balance_amount = Event.check_student_balance(student)

        # --- Determine event state ---
        if has_class:
            state = 'logged'
        else:
            state = 'ignored'

        # --- Create event record ---
        event_vals = {
            'student_id': student.id,
            'student_code': student_code,
            'device_id': device_id,
            'direction': direction,
            'event_datetime': event_dt,
            'has_class_now': has_class,
            'timetable_id': timetable.id if timetable else False,
            'balance_ok': balance_ok,
            'finance_balance_snapshot': balance_amount,
            'state': state,
            'raw_payload': body,
        }
        event = self._create_event(env, event_vals)

        # --- Enqueue Telegram notification (fire-and-forget) ---
        if student.telegram_notifications_enabled:
            event._enqueue_notification()

        # --- Build response ---
        group_name = None
        if timetable:
            group_name = timetable.group_id.name if timetable.group_id else None

        response_status = 'ok'
        message = None
        if not has_class:
            response_status = 'warning'
            message = 'No scheduled class at this time'
        elif not balance_ok:
            response_status = 'warning'
            message = 'Student balance is insufficient (payment pending)'

        response_data = {
            'status': response_status,
            'student_name': student.name,
            'has_class_now': has_class,
            'group_name': group_name,
            'balance_ok': balance_ok,
            'event_id': event.id,
        }
        if message:
            response_data['message'] = message

        # --- Record processing time and response ---
        elapsed_ms = int((time.time() - start_time) * 1000)
        event.write({
            'processing_time_ms': elapsed_ms,
            'response_payload': json.dumps(response_data, ensure_ascii=False),
        })

        _logger.info(
            "FaceID API: student=%s code=%s device=%s has_class=%s "
            "balance_ok=%s event_id=%d elapsed=%dms",
            student.name, student_code, device_id,
            has_class, balance_ok, event.id, elapsed_ms,
        )

        return self._json_response(response_data)

    # ==================================================================
    # HELPERS
    # ==================================================================
    def _check_api_key(self):
        """Validate the X-Api-Key header against the stored shared secret.

        Returns:
            None if valid, or a JSON error response if invalid.
        """
        expected_key = request.env['ir.config_parameter'].sudo().get_param(
            API_KEY_PARAM, default=''
        )
        if not expected_key:
            # No key configured = endpoint is open (development mode)
            _logger.warning(
                "FaceID API: no API key configured (%s). "
                "Endpoint is unprotected!", API_KEY_PARAM
            )
            return None

        provided_key = request.httprequest.headers.get('X-Api-Key', '').strip()
        if not provided_key:
            return self._json_response({
                'status': 'error',
                'message': 'Missing X-Api-Key header',
            }, status=401)

        # Constant-time comparison to prevent timing attacks
        import hmac
        if not hmac.compare_digest(provided_key, expected_key):
            _logger.warning(
                "FaceID API: invalid API key from %s",
                request.httprequest.remote_addr,
            )
            return self._json_response({
                'status': 'error',
                'message': 'Invalid API key',
            }, status=401)

        return None

    def _parse_timestamp(self, timestamp_str):
        """Parse an ISO 8601 timestamp, falling back to server time.

        Accepts various formats:
          - "2025-01-15T14:02:00Z"
          - "2025-01-15T14:02:00+05:00"
          - "2025-01-15 14:02:00"
          - "" (empty, uses server time)
        """
        if not timestamp_str:
            return odoo_fields.Datetime.now()

        # Try common ISO formats
        for fmt in (
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S%z',
        ):
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                # Convert to UTC naive (Odoo convention)
                if dt.tzinfo:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except ValueError:
                continue

        # Last resort: strip timezone suffix and try
        try:
            # Handle "+05:00" suffix
            clean = timestamp_str
            if '+' in clean[10:]:
                clean = clean[:clean.rindex('+')]
            elif clean.endswith('Z'):
                clean = clean[:-1]
            dt = datetime.strptime(clean, '%Y-%m-%dT%H:%M:%S')
            return dt
        except (ValueError, IndexError):
            pass

        _logger.warning(
            "FaceID API: could not parse timestamp '%s', using server time",
            timestamp_str,
        )
        return odoo_fields.Datetime.now()

    def _create_event(self, env, vals):
        """Create an edu.faceid.event record.

        Args:
            env: Odoo environment (sudo).
            vals: dict of field values.

        Returns:
            edu.faceid.event record.
        """
        return env['edu.faceid.event'].create(vals)

    def _json_response(self, data, status=200):
        """Build a JSON HTTP response.

        Always returns the specified status code (default 200) so the
        turnstile device doesn't keep retrying.
        """
        body = json.dumps(data, ensure_ascii=False, default=str)
        headers = [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ]
        return request.make_response(body, status=status, headers=headers)
