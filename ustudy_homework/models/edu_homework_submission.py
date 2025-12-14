from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class EduHomeworkSubmission(models.Model):
    _name = "edu.homework.submission"
    _description = "Homework Submission"
    _order = "state, submit_date desc"

    homework_id = fields.Many2one(
        "edu.homework", string="Homework", required=True, ondelete="cascade"
    )
    student_id = fields.Many2one(
        "res.partner",
        string="Student",
        required=True,
        domain=[("is_student", "=", True)],
    )
    user_id = fields.Many2one("res.users", string="User", required=True)
    submit_date = fields.Datetime(
        string="Submitted On", default=fields.Datetime.now, required=True
    )
    comment = fields.Text(string="Student Comment")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "edu_homework_submission_ir_attachment_rel",
        "submission_id",
        "attachment_id",
        string="Files",
    )
    state = fields.Selection(
        [("submitted", "Submitted"), ("graded", "Graded")],
        default="submitted",
        string="Status",
    )

    # 🔹 teacher grading directly on submission
    mark = fields.Float(string="Mark")
    teacher_comment = fields.Text(string="Teacher Comment")

    # optional legacy relation – can be unused
    mark_id = fields.Many2one("edu.homework.mark", string="Mark Record")

    def _check_student_access(self):
        user = self.env.user
        if user._is_admin():
            return
        if any(s.user_id != user for s in self):
            raise AccessError(_("You can only see your own submissions."))
        
        
    # --- AUTO-UPDATE STATE WHEN MARK CHANGES ---------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'mark' in vals:
                # if mark is provided (even 0.0), consider it graded
                if vals['mark'] is not False and vals['mark'] is not None:
                    vals.setdefault('state', 'graded')
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)  # copy, Odoo may reuse dict
        if 'mark' in vals:
            # 0.0 is a valid grade → graded
            if vals['mark'] is not False and vals['mark'] is not None:
                vals['state'] = 'graded'
            else:
                vals['state'] = 'submitted'
        return super().write(vals)

    # -------------------------------------------------------------------------