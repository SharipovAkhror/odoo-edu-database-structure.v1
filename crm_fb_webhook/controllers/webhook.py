import json
import hmac
import hashlib
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class FacebookWebhookController(http.Controller):

    # ---------------------------------------------------------------
    # GET /fb/webhook
    # Facebook calls this once when you register the webhook URL.
    # Must respond with hub.challenge to confirm ownership.
    # ---------------------------------------------------------------
    @http.route(
        '/fb/webhook',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
    )
    def fb_verify(self, **kwargs):
        verify_token = (
            request.env['ir.config_parameter']
            .sudo()
            .get_param('crm_fb_webhook.verify_token', '')
        )
        mode = kwargs.get('hub.mode', '')
        token = kwargs.get('hub.verify_token', '')
        challenge = kwargs.get('hub.challenge', '')

        if mode == 'subscribe' and token == verify_token:
            _logger.info('Facebook webhook endpoint verified successfully')
            return request.make_response(challenge)

        _logger.warning('Facebook webhook verification failed — token mismatch or wrong mode')
        return request.make_response('Forbidden', status=403)

    # ---------------------------------------------------------------
    # POST /fb/webhook
    # Facebook sends a lead event payload here the moment a user
    # submits a Lead Ad form.
    # ---------------------------------------------------------------
    @http.route(
        '/fb/webhook',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def fb_lead_event(self, **kwargs):
        raw_body = request.httprequest.get_data()

        # --- Verify HMAC-SHA256 signature (prevents spoofed requests) ---
        app_secret = (
            request.env['ir.config_parameter']
            .sudo()
            .get_param('crm_fb_webhook.app_secret', '')
        )
        if app_secret:
            sig_header = request.httprequest.headers.get('X-Hub-Signature-256', '')
            expected = 'sha256=' + hmac.new(
                app_secret.encode('utf-8'),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(sig_header, expected):
                _logger.warning('Facebook webhook: invalid signature — request rejected')
                return request.make_response('Forbidden', status=403)

        # --- Parse JSON ---
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            _logger.error('Facebook webhook: could not parse JSON body')
            return request.make_response('Bad Request', status=400)

        # --- Process lead entries ---
        # Payload structure:
        # {
        #   "object": "page",
        #   "entry": [{
        #     "id": "<PAGE_ID>",
        #     "changes": [{
        #       "field": "leadgen",
        #       "value": {
        #         "leadgen_id": "...",
        #         "page_id": "...",
        #         "form_id": "...",
        #         "ad_id": "...",
        #         "created_time": 1234567890
        #       }
        #     }]
        #   }]
        # }
        if payload.get('object') == 'page':
            for entry in payload.get('entry', []):
                page_id = str(entry.get('id', ''))
                for change in entry.get('changes', []):
                    if change.get('field') != 'leadgen':
                        continue
                    val = change.get('value', {})
                    leadgen_id = val.get('leadgen_id')
                    form_id = str(val.get('form_id', ''))
                    if leadgen_id and form_id:
                        try:
                            request.env['fb.page'].sudo()._process_incoming_lead(
                                page_id=page_id,
                                form_id=form_id,
                                leadgen_id=str(leadgen_id),
                            )
                        except Exception:
                            # Never let an error break the 200 response —
                            # Facebook retries for 36 hours on non-200
                            _logger.exception(
                                'Error processing Facebook lead leadgen_id=%s', leadgen_id
                            )

        # Facebook REQUIRES HTTP 200 to stop retrying
        return request.make_response('EVENT_RECEIVED')
