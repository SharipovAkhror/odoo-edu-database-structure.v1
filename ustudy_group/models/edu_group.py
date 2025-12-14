from odoo import api, fields, models


class EduGroup(models.Model):
    _name = "edu.group"
    _description = "Student Group"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Group Name", required=True, tracking=True)

    course_id = fields.Many2one(
        "edu.course",
        string="Course",
        required=True,
        tracking=True,
    )

    teacher_id = fields.Many2one(
        "hr.employee",
        string="Teacher",
        tracking=True,
        ondelete="set null",
    )

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("done", "Finished"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    student_line_ids = fields.One2many(
        "edu.group.student",
        "group_id",
        string="Students",
    )

    student_count = fields.Integer(
        string="Students",
        compute="_compute_student_count",
        store=False,
    )

    @api.depends("student_line_ids")
    def _compute_student_count(self):
        for group in self:
            group.student_count = len(group.student_line_ids)


class EduGroupStudent(models.Model):
    _name = "edu.group.student"
    _description = "Group Student"

    group_id = fields.Many2one(
        "edu.group",
        string="Group",
        required=True,
        ondelete="cascade",
    )

    student_id = fields.Many2one(
        "res.partner",
        string="Student",
        required=True,
        domain="[('is_student', '=', True)]",
    )

    # convenience/readonly fields for display
    student_name = fields.Char(
        string="Full Name",
        related="student_id.name",
        store=False,
    )
    total_courses = fields.Integer(
        string="Courses",
        related="student_id.total_courses",
        store=False,
    )
    avg_progress = fields.Float(
        string="Avg Progress",
        related="student_id.avg_progress",
        store=False,
    )
    avg_mark = fields.Float(
        string="Avg Mark",
        related="student_id.avg_mark",
        store=False,
    )

    state = fields.Selection(
        [
            ("active", "Active"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="active",
    )

    _sql_constraints = [
        (
            "group_student_unique",
            "unique(group_id, student_id)",
            "Student already exists in this group.",
        )
    ]
