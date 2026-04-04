from odoo import api, fields, models, _

class EduModule(models.Model):
    _name = "edu.module"
    _description = "Education Module"
    _order = "sequence asc, id asc"

    name = fields.Char(string="Module Name", required=True)
    sequence = fields.Integer(string="Sequence", default=1)

    active = fields.Boolean(default=True)

