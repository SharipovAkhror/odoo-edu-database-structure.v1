# ustudy_homework/models/edu_timetable.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class EduTimetable(models.Model):
    _inherit = "edu.timetable"

    homework_id = fields.Many2one(
        "edu.homework",
        string="Homework",
        compute="_compute_homework_id",
        store=True,          # ✅ MUHIM
        index=True,
    )

    submitted_count = fields.Integer(compute="_compute_homework_stats", store=False)
    group_student_count = fields.Integer(compute="_compute_homework_stats", store=False)
    submission_ratio = fields.Char(compute="_compute_homework_stats", store=False)

    @api.depends("slide_id", "slide_channel_id")
    def _compute_homework_id(self):
        Homework = self.env["edu.homework"]
        for rec in self:
            hw = False
            if rec.slide_id:
                hw = Homework.search([
                    ("slide_id", "=", rec.slide_id.id),
                    ("is_published", "=", True),
                ], limit=1)
            if not hw and rec.slide_channel_id:
                hw = Homework.search([
                    ("channel_id", "=", rec.slide_channel_id.id),
                    ("is_published", "=", True),
                ], limit=1)
            rec.homework_id = hw.id if hw else False

    def _group_student_partner_ids(self):
        self.ensure_one()
        return self.group_id.student_line_ids.mapped("student_id").ids

    @api.depends("group_id", "homework_id")
    def _compute_homework_stats(self):
        Submission = self.env["edu.homework.submission"]
        for rec in self:
            total = rec.group_id.student_count or 0
            rec.group_student_count = total

            if not rec.homework_id or total == 0:
                rec.submitted_count = 0
                rec.submission_ratio = f"0/{total}" if total else "0/0"
                continue

            student_ids = rec._group_student_partner_ids()
            submitted = Submission.search_count([
                ("homework_id", "=", rec.homework_id.id),
                ("student_id", "in", student_ids),
            ])
            rec.submitted_count = submitted
            rec.submission_ratio = f"{submitted}/{total}"

    def action_view_group_homework_submissions(self):
        self.ensure_one()
        if not self.homework_id:
            raise UserError(_("No homework linked to this timetable lesson."))

        student_ids = self._group_student_partner_ids()
        return {
            "name": _("Submissions"),
            "type": "ir.actions.act_window",
            "res_model": "edu.homework.submission",
            "view_mode": "list,form",
            "domain": [
                ("homework_id", "=", self.homework_id.id),
                ("student_id", "in", student_ids),
            ],
        }
