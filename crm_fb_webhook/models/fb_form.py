from odoo import fields, models


class FbLeadForm(models.Model):
    _name = 'fb.lead.form'
    _description = 'Facebook Lead Form'
    _order = 'name'

    name = fields.Char(string='Form Name', required=True)
    fb_form_id = fields.Char(string='Facebook Form ID', required=True, index=True)
    page_id = fields.Many2one('fb.page', string='Page', required=True, ondelete='cascade')
    status = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', default='active')

    # Lead routing override per form
    team_id = fields.Many2one('crm.team', string='Sales Team')
    user_id = fields.Many2one('res.users', string='Salesperson')

    # Custom field mappings for this form
    mapping_ids = fields.One2many('fb.field.mapping', 'form_id', string='Field Mappings')


class FbFieldMapping(models.Model):
    _name = 'fb.field.mapping'
    _description = 'Facebook → Odoo Field Mapping'
    _order = 'fb_field'

    form_id = fields.Many2one('fb.lead.form', string='Form', required=True, ondelete='cascade')
    fb_field = fields.Char(
        string='Facebook Field Name',
        required=True,
        help='The "name" value from Facebook field_data. '
             'Examples: full_name, email, phone_number, company_name, custom_field_abc',
    )
    odoo_field = fields.Char(
        string='Odoo CRM Field',
        required=True,
        help='The technical field name on crm.lead. '
             'Examples: contact_name, email_from, phone, partner_name, description',
    )
