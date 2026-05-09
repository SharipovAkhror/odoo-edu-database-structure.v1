{
    'name': 'Facebook Lead Ads — CRM Webhook',
    'version': '19.0.1.0.0',
    'summary': 'Real-time Facebook Lead Ads to CRM via OAuth 2.0 + Webhook',
    'description': """
Facebook Lead Ads → Odoo CRM (real-time webhook)

Features:
- One-click OAuth 2.0 login — connect your Facebook account
- Auto-discover all Facebook Pages you manage
- Auto-fetch all Lead Forms per page
- Real-time webhook: new leads appear in CRM instantly (no polling)
- Per-form field mapping (Facebook field → CRM field)
- Auto-mapping for common fields (name, email, phone, city…)
- Webhook signature verification (HMAC-SHA256) — secure
- Duplicate lead prevention
- Assign leads to sales team / salesperson per form
    """,
    'category': 'CRM',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['crm', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'views/oauth_templates.xml',
        'views/fb_page_views.xml',
        'views/fb_form_views.xml',
        'views/crm_lead_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
}
