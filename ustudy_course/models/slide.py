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


    def get_my_homework_status(self):
        """Return latest submission state for this slide for current user (submitted/graded/failed) or False."""
        self.ensure_one()
        user = self.env.user
        if user._is_public():
            return False

        Submission = self.env["edu.homework.submission"].sudo()
        last_sub = Submission.search([
            ("homework_id.slide_id", "=", self.id),
            ("user_id", "=", user.id),
        ], order="submit_date desc, id desc", limit=1)

        return last_sub.state if last_sub else False


    @api.depends('question_ids', 'website_published', 'channel_id.is_member')
    def _compute_mark_complete_actions(self):
        super()._compute_mark_complete_actions()
        user = self.env.user
        if user._is_public():
            return
        for slide in self:
            # Find lesson this slide belongs to
            lesson = self.env['ustudy.course.lesson'].sudo().search([
                '|', '|',
                ('video_id', '=', slide.id),
                ('file_ids', 'in', [slide.id]),
                ('homework_id', '=', slide.id),
            ], limit=1)
            if not lesson or not lesson.homework_id:
                continue
            # Find edu.homework linked to lesson's homework slide
            homework = self.env['edu.homework'].sudo().search([
                ('slide_id', '=', lesson.homework_id.id)
            ], limit=1)
            if not homework:
                continue
            # Check if user has a graded submission
            submission = self.env['edu.homework.submission'].sudo().search([
                ('homework_id', '=', homework.id),
                ('user_id', '=', user.id),
                ('state', '=', 'graded'),
            ], limit=1)
            if not submission:
                slide.can_self_mark_completed = False