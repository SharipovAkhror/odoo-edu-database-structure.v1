from odoo import api, fields, models, _

class EduHomework(models.Model):
    _name = "edu.homework"
    _description = "Lesson Homework"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Title", required=True, tracking=True)
    slide_id = fields.Many2one('slide.slide', string='Lesson/Slide', ondelete='set null')

    channel_id = fields.Many2one(
        "slide.channel",
        string="Course / Channel",
        required=False,
        tracking=True,
        ondelete='set null',
        index=True,
    )

    description = fields.Text(string="Description")
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")
    due_date = fields.Date(string="Due Date")

    # now points to Employee
    teacher_id = fields.Many2one(
        "hr.employee",
        string="Teacher",
        ondelete="set null",
    )

    is_published = fields.Boolean(string="Published", default=True)

    mark_count = fields.Integer(string="Marks", compute="_compute_mark_count", store=False)
    mark_ids = fields.One2many("edu.homework.mark", "homework_id", string="Marks")

    submission_ids = fields.One2many("edu.homework.submission", "homework_id", string="Submissions")
    submission_count = fields.Integer(string="Submissions", compute="_compute_submission_count")

    @api.depends("submission_ids")
    def _compute_submission_count(self):
        for rec in self:
            rec.submission_count = len(rec.submission_ids)

    @api.depends("mark_ids")
    def _compute_mark_count(self):
        for rec in self:
            rec.mark_count = len(rec.mark_ids)

    @api.model
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        default_slide_id = self.env.context.get('default_slide_id')

        # set channel from slide
        for vals in vals_list:
            slide_id = vals.get('slide_id') or default_slide_id
            if slide_id and not vals.get('channel_id'):
                slide = self.env['slide.slide'].browse(slide_id)
                if slide and slide.channel_id:
                    vals['channel_id'] = slide.channel_id.id

        records = super(EduHomework, self).create(vals_list)

        # fallback teacher from edu.group (teacher is a res.users there)
        for rec in records:
            if not rec.teacher_id and rec.channel_id:
                group = self.env["edu.group"].search([
                    ("course_id", "=", rec.channel_id.id),
                    ("teacher_id", "!=", False)
                ], limit=1)
                if group and group.teacher_id:
                    # map user -> employee
                    employee = self.env["hr.employee"].search(
                        [("user_id", "=", group.teacher_id.id)],
                        limit=1,
                    )
                    if employee:
                        rec.teacher_id = employee.id

        return records

    def write(self, vals):
        # set channel from slide when slide changes
        if 'slide_id' in vals and vals.get('slide_id') and not vals.get('channel_id'):
            slide = self.env['slide.slide'].browse(vals.get('slide_id'))
            if slide and slide.channel_id:
                vals['channel_id'] = slide.channel_id.id

        res = super().write(vals)

        # same fallback teacher logic on write
        for rec in self.filtered(lambda r: not r.teacher_id and r.channel_id):
            group = self.env["edu.group"].search([
                ("course_id", "=", rec.channel_id.id),
                ("teacher_id", "!=", False)
            ], limit=1)
            if group and group.teacher_id:
                employee = self.env["hr.employee"].search(
                    [("user_id", "=", group.teacher_id.id)],
                    limit=1,
                )
                if employee:
                    rec.teacher_id = employee.id
        return res

    def action_open_marks(self):
        self.ensure_one()
        return {
            "name": _("Marks"),
            "type": "ir.actions.act_window",
            "res_model": "edu.homework.mark",
            "domain": [("homework_id", "=", self.id)],
            "view_mode": "list,form",
            "context": dict(self.env.context or {}, default_homework_id=self.id),
        }

    def unlink_slide(self):
        for rec in self:
            rec.slide_id = False
