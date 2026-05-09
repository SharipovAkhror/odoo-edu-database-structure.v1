import logging
from urllib.parse import urlencode

import requests as req
from werkzeug.utils import redirect as werkzeug_redirect

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

GRAPH = 'https://graph.facebook.com/v19.0'
FB_AUTH_URL = 'https://www.facebook.com/v19.0/dialog/oauth'
FB_TOKEN_URL = f'{GRAPH}/oauth/access_token'


class FacebookOAuthController(http.Controller):

    def _base_url(self):
        """
        Always return the public-facing base URL from ir.config_parameter.
        This was manually set to https://weteachprof.com and is the source of truth.
        """
        return request.env['ir.config_parameter'].sudo() \
            .get_param('web.base.url', '').rstrip('/')

    # ---------------------------------------------------------------
    # STEP 1 — Redirect browser to Facebook login dialog
    # ---------------------------------------------------------------
    @http.route('/fb/oauth/start', type='http', auth='user', methods=['GET'])
    def fb_oauth_start(self, **kwargs):
        ICP = request.env['ir.config_parameter'].sudo()
        app_id = ICP.get_param('crm_fb_webhook.app_id', '')
        if not app_id:
            return request.render('crm_fb_webhook.tpl_oauth_error', {
                'error': 'Facebook App ID is not set. Please fill it in CRM → Settings → Facebook first.',
            })

        redirect_uri = self._base_url() + '/fb/oauth/callback'

        params = urlencode({
            'client_id': app_id,
            'redirect_uri': redirect_uri,
            'scope': 'pages_show_list,pages_read_engagement,pages_manage_metadata,leads_retrieval,pages_manage_ads,ads_management',
            'response_type': 'code',
            'state': 'crm_fb_oauth',
        })

        # Use werkzeug_redirect directly — Odoo's request.redirect() strips
        # external hosts as an open-redirect security measure
        fb_url = f'{FB_AUTH_URL}?{params}'
        _logger.info('Redirecting to Facebook OAuth: %s', fb_url)
        return werkzeug_redirect(fb_url, code=302)

    # ---------------------------------------------------------------
    # STEP 2 — Facebook calls back here with ?code=...
    # ---------------------------------------------------------------
    @http.route('/fb/oauth/callback', type='http', auth='user', methods=['GET'])
    def fb_oauth_callback(self, code=None, error=None, error_description=None, **kwargs):
        if error:
            return request.render('crm_fb_webhook.tpl_oauth_error', {
                'error': f'Facebook denied access: {error_description or error}',
            })
        if not code:
            return request.render('crm_fb_webhook.tpl_oauth_error', {
                'error': 'No authorization code received from Facebook.',
            })

        ICP = request.env['ir.config_parameter'].sudo()
        app_id = ICP.get_param('crm_fb_webhook.app_id', '')
        app_secret = ICP.get_param('crm_fb_webhook.app_secret', '')
        redirect_uri = self._base_url() + '/fb/oauth/callback'

        # Exchange code for short-lived user token
        resp = req.get(FB_TOKEN_URL, params={
            'client_id': app_id,
            'client_secret': app_secret,
            'redirect_uri': redirect_uri,
            'code': code,
        }, timeout=15)

        if resp.status_code != 200:
            err = resp.json().get('error', {}).get('message', resp.text)
            return request.render('crm_fb_webhook.tpl_oauth_error', {
                'error': f'Token exchange failed: {err}',
            })

        short_token = resp.json().get('access_token', '')

        # Exchange for long-lived token (60 days)
        ll_resp = req.get(FB_TOKEN_URL, params={
            'grant_type': 'fb_exchange_token',
            'client_id': app_id,
            'client_secret': app_secret,
            'fb_exchange_token': short_token,
        }, timeout=15)

        user_token = ll_resp.json().get('access_token', short_token) \
            if ll_resp.status_code == 200 else short_token

        # Get connected user info
        me = req.get(f'{GRAPH}/me', params={
            'access_token': user_token,
            'fields': 'id,name',
        }, timeout=10)
        me_data = me.json() if me.status_code == 200 else {}

        # Persist tokens
        ICP.set_param('crm_fb_webhook.user_token', user_token)
        ICP.set_param('crm_fb_webhook.fb_user_id', me_data.get('id', ''))
        ICP.set_param('crm_fb_webhook.fb_user_name', me_data.get('name', ''))

        _logger.info('Facebook OAuth connected: %s (%s)', me_data.get('name'), me_data.get('id'))

        # Auto-sync pages and forms
        try:
            request.env['fb.page'].sudo()._sync_pages_from_facebook()
        except Exception:
            _logger.exception('Error syncing Facebook pages after OAuth')

        return request.redirect('/odoo/settings?searchTerms=Facebook')

    # ---------------------------------------------------------------
    # Disconnect — clear stored tokens
    # ---------------------------------------------------------------
    @http.route('/fb/oauth/disconnect', type='http', auth='user', methods=['GET'])
    def fb_oauth_disconnect(self, **kwargs):
        ICP = request.env['ir.config_parameter'].sudo()
        for key in ('crm_fb_webhook.user_token', 'crm_fb_webhook.fb_user_id',
                    'crm_fb_webhook.fb_user_name'):
            ICP.set_param(key, '')
        return request.redirect('/odoo/settings?searchTerms=Facebook')
