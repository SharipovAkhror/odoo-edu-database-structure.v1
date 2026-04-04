# /opt/education/custom-addons/ustudy_student/models/edu_enrollment.py
from odoo import fields, models, api


class EduEnrollment(models.Model):
    _name = "edu.enrollment"
    _description = "Course Enrollment"

    student_id = fields.Many2one(
        "res.partner",
        string="Student",
        required=True,
        ondelete='cascade',
        domain=[("is_student", "=", True)],
    )

    course_id = fields.Many2one(
        "edu.course",
        string="Course",
        required=True,
        ondelete='cascade', 
    )

    state = fields.Selection(
        [
            ("active", "Active"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="active",
    )

    progress = fields.Float(string="Progress (%)")
    xp = fields.Integer(string="XP")
    level = fields.Char(string="Level")
    paid = fields.Boolean(string="Paid")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            partner = record.student_id.sudo()

            # 1) email_verified ni PARTNERga yozamiz (field bor bo‘lsa)
            if 'email_verified' in partner._fields:
                partner.write({'email_verified': True})

            # 2) user bo‘lsa active ni userga yozamiz
            users = partner.user_ids.sudo()
            if users:
                users.write({'active': True})

        return records