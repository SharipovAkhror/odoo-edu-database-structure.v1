from odoo import api, fields, models

class Slide(models.Model):
    _inherit = "slide.slide"

    # extra fields
    is_homework = fields.Boolean("Homework")
    ustudy_lesson_id = fields.Many2one(
        "ustudy.course.lesson",
        string="Lesson",
        ondelete="set null",
        help="Optional direct link from content back to its lesson.",
    )

    # helper
    def _get_related_lesson_slides(self):
        """All slides for the same lesson as this slide (video, files, homework)."""
        self.ensure_one()
        lesson = self.ustudy_lesson_id
        if not lesson:
            return self

        slides = self.env['slide.slide']
        if lesson.video_id:
            slides |= lesson.video_id
        if lesson.file_ids:
            slides |= lesson.file_ids
        if lesson.homework_id:
            slides |= lesson.homework_id
        return slides or self

    def action_publish_slide(self):
        for slide in self:
            slides_to_publish = slide._get_related_lesson_slides()
            vals = {}
            if "is_published" in slide._fields:
                vals["is_published"] = True
            if "website_published" in slide._fields:
                vals["website_published"] = True
            if vals:
                slides_to_publish.write(vals)

    def action_unpublish_slide(self):
        for slide in self:
            slides_to_unpublish = slide._get_related_lesson_slides()
            vals = {}
            if "is_published" in slide._fields:
                vals["is_published"] = False
            if "website_published" in slide._fields:
                vals["website_published"] = False
            if vals:
                slides_to_unpublish.write(vals)
