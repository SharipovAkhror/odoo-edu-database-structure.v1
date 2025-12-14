# /opt/education/custom-addons/ustudy_student/models/edu_enrollment.py
from odoo import fields, models


class EduEnrollment(models.Model):
    _name = "edu.enrollment"
    _description = "Course Enrollment"

    student_id = fields.Many2one(
        "res.partner",
        string="Student",
        required=True,
        domain=[("is_student", "=", True)],
    )
    course_id = fields.Many2one(
        "edu.course",
        string="Course",
        required=True,
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
