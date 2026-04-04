# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CCFinance(models.Model):
    _inherit = "cc.finance"

    student_line_id = fields.Many2one(
        "edu.group.student",
        string="Student Group Line",
        ondelete="set null",
        index=True,
        readonly=True
    )

    group_id = fields.Many2one(
        "edu.group",
        string="Group",
        related="student_line_id.group_id",
        store=True,
        readonly=True
    )

    module_id = fields.Many2one(
        "edu.module",
        string="Module",
        ondelete="restrict",
        readonly=True,
        copy=False
    )

    student_status = fields.Selection(
        related="student_line_id.state",
        string="Student Status",
        store=True,
        readonly=True
    )

    payment_status = fields.Selection(
        related="student_line_id.payment_status",
        string="Payment Status",
        store=True,
        readonly=True
    )

    @api.onchange("student_line_id")
    def _onchange_student_line_id_set_module(self):
        for rec in self:
            if rec.student_line_id:
                rec.module_id = rec.student_line_id.current_module_id.id
            else:
                rec.module_id = False

    @api.onchange("partner_id")
    def _onchange_partner_id_set_student_line(self):
        for rec in self:
            rec.student_line_id = False

            if not rec.partner_id:
                continue

            line = self.env["edu.group.student"].search([
                ("student_id", "=", rec.partner_id.id),
                ("state", "!=", "cancelled")
            ], limit=1)

            if line:
                rec.student_line_id = line.id
