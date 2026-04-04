from odoo import api, fields, models


class EduWeekday(models.Model):
    _name = 'edu.weekday'
    _description = 'Weekday'
    _order = 'sequence'

    name = fields.Char(string='Day', required=True)
    sequence = fields.Integer(default=1)