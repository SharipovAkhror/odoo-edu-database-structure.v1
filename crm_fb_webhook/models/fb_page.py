import logging
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
GRAPH = 'https://graph.facebook.com/v19.0'

# Facebook standard field names → Odoo crm.lead field names
AUTO_MAP = {
    'full_name':      'contact_name',
    'first_name':     '_fb_first_name',   # handled specially below
    'last_name':      '_fb_last_name',    # handled specially below
    'email':          'email_from',
    'phone_number':   'phone',
    'phone':          'phone',
    'company_name':   'partner_name',
    'job_title':      'function',
    'city':           'city',
    'zip_code':       'zip',
    'street_address': 'street',
    'post_code':      'zip',
    'work_email':     'email_from',
}


class FbPage(models.Model):
    _name = 'fb.page'
    _description = 'Facebook Page'
    _order = 'name'

    name = fields.Char(string='Page Name', required=True, readonly=True)
    fb_page_id = fields.Char(string='Facebook Page ID', required=True, readonly=True, index=True)
    page_token = fields.Char(string='Page Access Token', readonly=True)
    webhook_subscribed = fields.Boolean(string='Webhook Active', default=False, readonly=True)

    team_id = fields.Many2one('crm.team', string='Default Sales Team')
    user_id = fields.Many2one('res.users', string='Default Salesperson',
                               default=lambda self: self.env.user)
    form_ids = fields.One2many('fb.lead.form', 'page_id', string='Lead Forms')
    form_count = fields.Integer(compute='_compute_form_count')
    active = fields.Boolean(default=True)

    def _compute_form_count(self):
        for rec in self:
            rec.form_count = len(rec.form_ids)

    # ---------------------------------------------------------------- actions
    def action_view_forms(self):
        self.ensure_one()
        return {
            'name': _('Lead Forms — %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'fb.lead.form',
            'view_mode': 'list,form',
            'domain': [('page_id', '=', self.id)],
            'context': {'default_page_id': self.id},
        }

    def action_sync_forms(self):
        self.ensure_one()
        count = self._fetch_forms()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Forms Synced'),
                'message': _('%d lead forms updated for %s') % (count, self.name),
                'type': 'success',
            },
        }

    def action_subscribe_webhook(self):
        self.ensure_one()
        self._subscribe_webhook()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Webhook Subscribed'),
                'message': _('"%s" will now receive leads in real-time.') % self.name,
                'type': 'success',
            },
        }

    def action_unsubscribe_webhook(self):
        self.ensure_one()
        self._unsubscribe_webhook()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Webhook Removed'),
                'message': _('Webhook unsubscribed for "%s".') % self.name,
                'type': 'warning',
            },
        }

    # ---------------------------------------------------------------- sync pages
    @api.model
    def action_sync_pages(self):
        """Button action: sync pages from Facebook."""
        count = self._sync_pages_from_facebook()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pages Synced'),
                'message': _('%d Facebook pages synced.') % count,
                'type': 'success',
            },
        }

    @api.model
    def _sync_pages_from_facebook(self):
        """
        Fetch all pages the connected Facebook user manages.
        GET /me/accounts → returns pages + per-page access tokens.
        Upserts fb.page records and fetches forms for each.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        user_token = ICP.get_param('crm_fb_webhook.user_token', '')
        if not user_token:
            raise UserError(_(
                'No Facebook account connected. '
                'Click "Connect Facebook Account" in CRM → Settings → Facebook.'
            ))

        url = f'{GRAPH}/me/accounts'
        params = {
            'access_token': user_token,
            'fields': 'id,name,access_token,category',
            'limit': 100,
        }
        pages_synced = 0

        while url:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                err = resp.json().get('error', {}).get('message', resp.text)
                raise UserError(_('Failed to fetch Facebook pages: %s') % err)

            data = resp.json()
            for page in data.get('data', []):
                fb_page_id = str(page['id'])
                vals = {
                    'name': page.get('name', fb_page_id),
                    'fb_page_id': fb_page_id,
                    'page_token': page.get('access_token', ''),
                }
                existing = self.search([('fb_page_id', '=', fb_page_id)], limit=1)
                if existing:
                    existing.write(vals)
                    existing._fetch_forms()
                else:
                    new_page = self.create(vals)
                    new_page._fetch_forms()
                pages_synced += 1

            # Follow pagination cursors
            next_url = data.get('paging', {}).get('next')
            if next_url:
                url = next_url
                params = {}
            else:
                break

        _logger.info('Facebook pages synced: %d', pages_synced)
        return pages_synced

    # ---------------------------------------------------------------- forms
    def _fetch_forms(self):
        """
        Fetch lead forms from GET /{page-id}/leadgen_forms.
        Creates fb.lead.form records; updates name/status of existing ones.
        Returns number of new forms created.
        """
        if not self.page_token:
            return 0

        url = f'{GRAPH}/{self.fb_page_id}/leadgen_forms'
        params = {
            'access_token': self.page_token,
            'fields': 'id,name,status',
            'limit': 100,
        }
        existing_ids = {f.fb_form_id for f in self.form_ids}
        created = 0

        while url:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                _logger.error('Error fetching forms for page %s: %s', self.fb_page_id, resp.text)
                break

            data = resp.json()
            for form in data.get('data', []):
                fid = str(form['id'])
                status = form.get('status', 'ACTIVE').lower()
                if fid not in existing_ids:
                    self.env['fb.lead.form'].create({
                        'page_id': self.id,
                        'fb_form_id': fid,
                        'name': form.get('name', fid),
                        'status': status,
                    })
                    existing_ids.add(fid)
                    created += 1
                else:
                    self.form_ids.filtered(lambda f: f.fb_form_id == fid).write({
                        'name': form.get('name', fid),
                        'status': status,
                    })

            next_url = data.get('paging', {}).get('next')
            if next_url:
                url = next_url
                params = {}
            else:
                break

        return created

    # ---------------------------------------------------------------- webhook subscription
    def _subscribe_webhook(self):
        """
        Subscribe this page's installed app to leadgen webhook events.
        POST /{page-id}/subscribed_apps  (requires page token)
        """
        if not self.page_token:
            raise UserError(_('Page "%s" has no access token.') % self.name)

        resp = requests.post(
            f'{GRAPH}/{self.fb_page_id}/subscribed_apps',
            params={
                'access_token': self.page_token,
                'subscribed_fields': 'leadgen',
            },
            timeout=10,
        )
        result = resp.json()
        if result.get('success'):
            self.webhook_subscribed = True
            _logger.info('Webhook subscribed for page %s', self.name)
        else:
            err = result.get('error', {}).get('message', str(result))
            raise UserError(_('Webhook subscription failed for "%s": %s') % (self.name, err))

    def _unsubscribe_webhook(self):
        if not self.page_token:
            return
        requests.delete(
            f'{GRAPH}/{self.fb_page_id}/subscribed_apps',
            params={
                'access_token': self.page_token,
                'subscribed_fields': 'leadgen',
            },
            timeout=10,
        )
        self.webhook_subscribed = False

    # ---------------------------------------------------------------- lead processing
    @api.model
    def _process_incoming_lead(self, page_id, form_id, leadgen_id):
        """
        Called by the webhook controller for every new lead event.
        1. Find the page config.
        2. Deduplicate.
        3. Fetch full lead data from Graph API.
        4. Map fields → create crm.lead.
        """
        page = self.search([('fb_page_id', '=', page_id)], limit=1)
        if not page:
            _logger.warning(
                'No fb.page config for page_id=%s — sync pages in CRM Settings.', page_id
            )
            return

        if not page.page_token:
            _logger.error('Page %s has no token, cannot fetch lead', page.name)
            return

        # Deduplicate: Facebook retries on timeout so same leadgen_id can arrive twice
        if self.env['crm.lead'].sudo().search_count([('fb_leadgen_id', '=', leadgen_id)]):
            _logger.info('Duplicate lead leadgen_id=%s — skipped', leadgen_id)
            return

        # Fetch full lead data
        resp = requests.get(
            f'{GRAPH}/{leadgen_id}',
            params={
                'access_token': page.page_token,
                'fields': 'id,created_time,ad_id,ad_name,form_id,field_data',
            },
            timeout=15,
        )
        if resp.status_code != 200:
            _logger.error('Graph API error fetching lead %s: %s', leadgen_id, resp.text)
            return

        raw = resp.json()
        # field_data is a list: [{"name": "full_name", "values": ["Ali Valiyev"]}, ...]
        field_data = {
            f['name']: (f['values'][0] if f.get('values') else '')
            for f in raw.get('field_data', [])
        }
        _logger.debug('Facebook lead %s field_data: %s', leadgen_id, field_data)

        # Find form config for custom mappings
        form = page.form_ids.filtered(lambda f: f.fb_form_id == form_id)

        # Start building crm.lead values
        lead_vals = {
            'fb_leadgen_id': leadgen_id,
            'fb_page_id': page.id,
            'fb_form_id': form.id if form else False,
            'name': raw.get('ad_name') or f'Facebook Lead — {page.name}',
            'team_id': (form and form.team_id.id) or page.team_id.id or False,
            'user_id': (form and form.user_id.id) or page.user_id.id or False,
            'description': '',
        }

        # 1. Apply custom per-form field mappings first (highest priority)
        mapped_keys = set()
        crm_fields = self.env['crm.lead']._fields
        for mapping in (form.mapping_ids if form else []):
            val = field_data.get(mapping.fb_field, '')
            if val and mapping.odoo_field in crm_fields:
                lead_vals[mapping.odoo_field] = val
                mapped_keys.add(mapping.fb_field)

        # 2. Auto-map standard Facebook field names
        first = field_data.get('first_name', '')
        last = field_data.get('last_name', '')
        if first or last:
            combined = (first + ' ' + last).strip()
            if 'full_name' not in field_data and 'contact_name' not in lead_vals:
                lead_vals['contact_name'] = combined
            mapped_keys.update(['first_name', 'last_name'])

        for fb_key, odoo_key in AUTO_MAP.items():
            if fb_key in mapped_keys or odoo_key.startswith('_fb_'):
                continue
            val = field_data.get(fb_key, '')
            if val and odoo_key in crm_fields and odoo_key not in lead_vals:
                lead_vals[odoo_key] = val
                mapped_keys.add(fb_key)

        # 3. Remaining unmapped fields → description
        unmapped = [
            f'{k}: {v}' for k, v in field_data.items()
            if k not in mapped_keys and v
        ]
        if unmapped:
            lead_vals['description'] = '\n'.join(unmapped)

        # Set a sensible lead name
        if lead_vals.get('contact_name'):
            lead_vals['name'] = lead_vals['contact_name']
        elif lead_vals.get('email_from'):
            lead_vals['name'] = lead_vals['email_from']

        lead = self.env['crm.lead'].sudo().create(lead_vals)
        _logger.info(
            'Created crm.lead id=%d name="%s" from Facebook leadgen_id=%s',
            lead.id, lead.name, leadgen_id,
        )
        return lead
