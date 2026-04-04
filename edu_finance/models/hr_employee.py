# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Admin-only editable field
    finance_adjustment = fields.Float(
        string='Finance Adjustment (%)',
        default=0.0,
        tracking=True,
        help='Manual adjustment percentage to employee balance (Admin only)'
    )
    
    # Helper field to check if user is admin
    is_user_admin = fields.Boolean(
        string='Is Admin',
        compute='_compute_is_user_admin',
        compute_sudo=False
    )
    
    finance_balance = fields.Float(
        string='Finance Balance',
        default=0.0,
        tracking=True
    )
    
    finance_ids = fields.One2many(
        'cc.finance',
        'employee_id',
        string='Finance Records'
    )
    
    finance_count = fields.Integer(
        string='Finance Count',
        compute='_compute_finance_count'
    )
    
    def _compute_is_user_admin(self):
        """Check if current user is administrator"""
        is_admin = self.env.user.has_group('base.group_system')
        for record in self:
            record.is_user_admin = is_admin
    
    @api.depends('finance_ids')
    def _compute_finance_count(self):
        for employee in self:
            employee.finance_count = len(employee.finance_ids)
    
    def action_view_finances(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Finance Records',
            'res_model': 'cc.finance',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id}
        }