# /opt/education/custom-addons/ustudy_student/models/edu_course.py
from odoo import fields, models, api


class EduCourse(models.Model):
    _name = "edu.course"
    _description = "Course"

    name = fields.Char(string="Course Name", required=True, translate=True)

    active = fields.Boolean(
        compute='_compute_active',
        store=True,
        default=True,
    )

    @api.depends('slide_channel_id', 'slide_channel_id.active')
    def _compute_active(self):
        for rec in self:
            if rec.slide_channel_id:
                rec.active = rec.slide_channel_id.active
            else:
                rec.active = True
    code = fields.Char(string="Code")
    description = fields.Text(string="Description", translate=True)

    teacher_id = fields.Many2one("res.users", string="Teacher")

    list_price = fields.Float(string="Price")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id.id,
    )

    is_published = fields.Boolean(string="Published", default=True)

    slide_channel_id = fields.Many2one(
        "slide.channel",
        string="eLearning Course",
        ondelete="cascade",
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )

    enrollment_ids = fields.One2many(
        "edu.enrollment",
        "course_id",
        string="Enrollments",
    )
    student_count = fields.Integer(
        string="Student Count",
        compute="_compute_student_count",
        store=False,
    )

    def _compute_student_count(self):
        for course in self:
            course.student_count = len(course.enrollment_ids)

    @api.model
    def get_or_create_from_channel(self, channel):
        course = self.search([("slide_channel_id", "=", channel.id)], limit=1)
        if not course:
            course = self.create({
                "name": channel.name,
                "slide_channel_id": channel.id,
                "is_published": channel.is_published,
            })
        return course

    def unlink(self):
        # Delete all enrollments before deleting the course
        enrollments = self.env['edu.enrollment'].search([
            ('course_id', 'in', self.ids)
        ])
        if enrollments:
            enrollments.unlink()
        return super(EduCourse, self).unlink()