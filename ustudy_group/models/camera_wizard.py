from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CameraWizard(models.TransientModel):
    _name = 'edu.camera.wizard'
    _description = 'Teacher Camera Capture'

    timetable_id = fields.Many2one('edu.timetable', string='Lesson', required=True)
    teacher_image = fields.Binary("Teacher Photo")

    def action_capture_and_start(self):
        """Save image and create attendance"""
        self.ensure_one()

        is_admin = self.env.user.has_group("base.group_system")

        # If not admin, photo is required
        if not is_admin and not self.teacher_image:
            raise UserError(_("Please capture teacher photo first."))

        vals = {
            "timetable_id": self.timetable_id.id,
        }

        # If teacher photo exists, save it
        if self.teacher_image:
            vals.update({
                "teacher_start_image": self.teacher_image,
                "teacher_start_image_filename": f"teacher_start_{fields.Datetime.now()}.jpg",
            })

        # Create attendance record
        attendance = self.env["edu.attendance"].create(vals)

        # Create attendance lines for students
        attendance_lines = []
        for student_line in self.timetable_id.group_id.student_line_ids.filtered(lambda s: s.state == "active"):
            attendance_lines.append((0, 0, {
                "student_id": student_line.student_id.id,
                "status": "present",
            }))

        if attendance_lines:
            attendance.write({"attendance_line_ids": attendance_lines})

        # Mark lesson as in progress
        self.timetable_id.write({"state": "in_progress"})

        # Open attendance form
        return {
            "name": _("Mark Attendance"),
            "type": "ir.actions.act_window",
            "res_model": "edu.attendance",
            "res_id": attendance.id,
            "view_mode": "form",
            "target": "current",
        }
