# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    finance_balance = fields.Float(string='Finance Balance', default=0.0)
    finance_ids = fields.One2many('cc.finance', 'partner_id', string='Finance Records')
    finance_count = fields.Integer(string='Finance Count', compute='_compute_finance_count')
    
    @api.depends('finance_ids')
    def _compute_finance_count(self):
        for partner in self:
            partner.finance_count = len(partner.finance_ids)
    
    def action_view_finances(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Finance Records',
            'res_model': 'cc.finance',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }