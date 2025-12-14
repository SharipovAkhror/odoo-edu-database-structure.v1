from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    group_student_ids = fields.One2many(
        "edu.group.student",
        "student_id",
        string="Groups",
    )

    group_count = fields.Integer(
        string="Groups",
        compute="_compute_group_count",
        store=False,
    )

    def _compute_group_count(self):
        for partner in self:
            partner.group_count = len(partner.group_student_ids)

    def action_view_groups(self):
        """Smart button: open groups that contain this student."""
        self.ensure_one()
        action = self.env.ref("ustudy_group.action_edu_group_list").read()[0]
        # only groups where this partner is in student_line_ids
        action["domain"] = [("student_line_ids.student_id", "=", self.id)]
        action["context"] = dict(self.env.context or {}, default_student_id=self.id)
        return action
