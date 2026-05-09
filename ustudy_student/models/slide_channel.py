from odoo import api, models


class SlideChannel(models.Model):
    _inherit = "slide.channel"

    @api.model_create_multi
    def create(self, vals_list):
        channels = super().create(vals_list)
        EduCourse = self.env["edu.course"]
        for channel in channels:
            if not EduCourse.search([("slide_channel_id", "=", channel.id)], limit=1):
                EduCourse.create({
                    "name": channel.name,
                    "slide_channel_id": channel.id,
                    "is_published": channel.is_published,
                    "company_id": self.env.company.id,
                })
        return channels

    def write(self, vals):
        result = super().write(vals)
        if "name" in vals:
            for channel in self:
                course = self.env["edu.course"].search([
                    ("slide_channel_id", "=", channel.id)
                ], limit=1)
                if course:
                    course.name = channel.name
        return result
