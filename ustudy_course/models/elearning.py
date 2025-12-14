# ustudy_course/models/elearning.py
from odoo import api, fields, models


class SlideChannel(models.Model):
    _inherit = "slide.channel"

    ustudy_module_ids = fields.One2many(
        "ustudy.course.module", "channel_id", string="Modules"
    )
    ustudy_module_count = fields.Integer(
        string="Modules", compute="_compute_ustudy_module_count"
    )

    def _compute_ustudy_module_count(self):
        for channel in self:
            channel.ustudy_module_count = len(channel.ustudy_module_ids)

class UstudyCourseModule(models.Model):
    _name = "ustudy.course.module"
    _description = "Course Module"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)

    channel_id = fields.Many2one(
        "slide.channel",
        string="Course",
        required=True,
        ondelete="cascade",
    )

    lesson_ids = fields.One2many(
        "ustudy.course.lesson", "module_id", string="Lessons"
    )
    lesson_count = fields.Integer(
        string="Lessons", compute="_compute_lesson_count"
    )

    def _compute_lesson_count(self):
        for module in self:
            module.lesson_count = len(module.lesson_ids)


class UstudyCourseLesson(models.Model):
    _name = "ustudy.course.lesson"
    _description = "Course Lesson"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)

    module_id = fields.Many2one(
        "ustudy.course.module",
        string="Module",
        required=True,
        ondelete="cascade",
    )
    channel_id = fields.Many2one(
        "slide.channel",
        string="Course",
        related="module_id.channel_id",
        store=True,
        readonly=True,
    )

    # main video of lesson
    video_id = fields.Many2one(
        "slide.slide",
        string="Video",
        domain="[('channel_id', '=', channel_id), ('slide_category', '=', 'video')]",
    )

    # attached files for lesson
    file_ids = fields.Many2many(
        "slide.slide",
        "ustudy_lesson_file_rel",
        "lesson_id",
        "slide_id",
        string="Files",
        domain="[('channel_id', '=', channel_id), "
               "('slide_category', 'in', ['document', 'presentation'])]",
    )

    # homework slide (quiz, document, whatever you prefer)
    homework_id = fields.Many2one(
        "slide.slide",
        string="Homework",
        domain="[('channel_id', '=', channel_id), ('is_homework', '=', True)]",
    )


class Slide(models.Model):
    _inherit = "slide.slide"

    is_homework = fields.Boolean("Homework")
    ustudy_lesson_id = fields.Many2one(
        "ustudy.course.lesson",
        string="Lesson",
        ondelete="set null",
        help="Optional direct link from content back to its lesson.",
    )
