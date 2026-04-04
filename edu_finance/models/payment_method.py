# -*- coding: utf-8 -*-
from odoo import models, fields


class CCPaymentMethod(models.Model):
    _name = 'cc.payment.method'
    _description = 'Payment Method'
    _order = 'sequence, name'

    name = fields.Char(string='Method Name', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Payment method name must be unique!')
    ]