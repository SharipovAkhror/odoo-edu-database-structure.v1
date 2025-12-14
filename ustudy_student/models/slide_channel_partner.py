# /opt/education/custom-addons/ustudy_student/models/slide_channel_partner.py
from odoo import api, fields, models


class SlideChannelPartner(models.Model):
    _inherit = "slide.channel.partner"

    # Attendee = student bo'lsin, faqat is_student=True kontaktlar ko'rinsin
    partner_id = fields.Many2one(
        "res.partner",
        string="Student",
        domain="[('is_student', '=', True)]",
    )

    edu_enrollment_id = fields.Many2one(
        "edu.enrollment",
        string="Education Enrollment",
        ondelete="set null",
    )

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._sync_to_edu_enrollment()
        return rec

    def write(self, vals):
        res = super().write(vals)
        self._sync_to_edu_enrollment()
        return res

    def _sync_to_edu_enrollment(self):
        EduCourse = self.env["edu.course"]
        Enrollment = self.env["edu.enrollment"]

        for rec in self:
            if not rec.partner_id or not rec.channel_id:
                continue

            # Agar contact student bo'lmasa - student qilib qo'yamiz
            if not rec.partner_id.is_student:
                rec.partner_id.is_student = True

            # slide.channel dan edu.course ni topish / yaratish
            course = EduCourse.get_or_create_from_channel(rec.channel_id)

            vals = {
                "student_id": rec.partner_id.id,
                "course_id": course.id,
                "state": "active",
                "progress": rec.completion or 0.0,
            }

            if rec.edu_enrollment_id:
                rec.edu_enrollment_id.write(vals)
            else:
                enrollment = Enrollment.create(vals)
                rec.edu_enrollment_id = enrollment.id
