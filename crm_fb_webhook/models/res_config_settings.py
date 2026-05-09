import secrets
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fb_app_id = fields.Char(
        string='App ID',
        config_parameter='crm_fb_webhook.app_id',
    )
    fb_app_secret = fields.Char(
        string='App Secret',
        config_parameter='crm_fb_webhook.app_secret',
    )
    fb_verify_token = fields.Char(
        string='Webhook Verify Token',
        config_parameter='crm_fb_webhook.verify_token',
    )

    # These are computed from ir.config_parameter directly (not stored on the transient)
    fb_user_name = fields.Char(compute='_compute_fb_connection_info')
    fb_is_connected = fields.Boolean(compute='_compute_fb_connection_info')
    fb_webhook_url = fields.Char(compute='_compute_fb_webhook_url')

    def _compute_fb_connection_info(self):
        ICP = self.env['ir.config_parameter'].sudo()
        name = ICP.get_param('crm_fb_webhook.fb_user_name', '')
        uid = ICP.get_param('crm_fb_webhook.fb_user_id', '')
        for rec in self:
            rec.fb_user_name = name or ''
            rec.fb_is_connected = bool(uid)

    def _compute_fb_webhook_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        for rec in self:
            rec.fb_webhook_url = f'{base}/fb/webhook'

    def action_connect_facebook(self):
        """
        Save the current settings (so App ID/Secret are persisted),
        then redirect the browser to the Facebook OAuth start URL.
        """
        # Persist config_parameter fields by calling execute()
        self.execute()

        ICP = self.env['ir.config_parameter'].sudo()
        app_id = ICP.get_param('crm_fb_webhook.app_id', '')
        if not app_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Missing App ID'),
                    'message': _('Please enter the Facebook App ID before connecting.'),
                    'type': 'danger',
                    'sticky': True,
                },
            }

        base = ICP.get_param('web.base.url', '').rstrip('/')
        return {
            'type': 'ir.actions.act_url',
            'url': f'{base}/fb/oauth/start',
            'target': 'self',
        }

    def action_generate_verify_token(self):
        token = secrets.token_urlsafe(32)
        self.env['ir.config_parameter'].sudo().set_param(
            'crm_fb_webhook.verify_token', token
        )
        # Also save any other pending changes
        self.execute()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Token Generated'),
                'message': _('Verify token saved. Copy it to your Facebook App → Webhooks → Verify Token.'),
                'type': 'success',
            },
        }

    def action_sync_pages(self):
        return self.env['fb.page'].action_sync_pages()
