from odoo import api, fields, models


class EduWeekday(models.Model):
    _name = 'edu.room'
    _description = 'Rooms'
    _order = 'sequence'

    name = fields.Char(string='Room Name', required=True)
    capacity = fields.Integer(string='Capacity')
    sequence = fields.Integer(default=1)    
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )