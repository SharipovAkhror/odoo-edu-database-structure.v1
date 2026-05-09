from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    fb_leadgen_id = fields.Char(
        string='Facebook Lead ID',
        index=True,
        copy=False,
        help='Facebook leadgen_id — used to prevent duplicate imports.',
    )
    fb_page_id = fields.Many2one(
        'fb.page',
        string='Facebook Page',
        ondelete='set null',
    )
    fb_form_id = fields.Many2one(
        'fb.lead.form',
        string='Facebook Form',
        ondelete='set null',
    )
