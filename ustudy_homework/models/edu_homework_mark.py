from odoo import api, fields, models, _


class EduHomeworkMark(models.Model):
    _name = "edu.homework.mark"
    _description = "Homework Mark"

    homework_id = fields.Many2one(
        "edu.homework",
        string="Homework",
        required=True,
        ondelete="cascade",
    )
    student_id = fields.Many2one(
        "res.partner",
        string="Student",
        required=True,
        domain="[('is_student','=',True)]",
    )
    teacher_id = fields.Many2one("hr.employee", string="Teacher")
    mark = fields.Float(string="Mark", digits=(6, 2))
    max_mark = fields.Float(string="Max Mark", default=100.0)
    comment = fields.Text(string="Teacher Comment")
    date = fields.Datetime(string="Marked On", default=fields.Datetime.now)

    student_name = fields.Char(related="student_id.name", store=False)
    homework_title = fields.Char(related="homework_id.name", store=False)

    @api.onchange("homework_id")
    def _onchange_homework_id(self):
        if self.homework_id and not self.teacher_id:
            self.teacher_id = (
                self.homework_id.teacher_id and self.homework_id.teacher_id.id or False
            )

    _sql_constraints = [
        (
            "unique_homework_student",
            "unique(homework_id, student_id)",
            "This student already has a mark for this homework.",
        ),
    ]
