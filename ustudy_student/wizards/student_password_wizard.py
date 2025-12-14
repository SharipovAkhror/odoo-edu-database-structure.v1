from odoo import models, fields
from odoo.exceptions import UserError


class StudentPasswordWizard(models.TransientModel):
    _name = "student.password.wizard"
    _description = "Set Portal User Password"

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        default=lambda self: self.env.context.get("active_id"),
    )
    new_password = fields.Char("New Password", required=True)

    def action_set_password(self):
        self.ensure_one()

        if not self.partner_id.user_ids:
            raise UserError("This student has no user account.")

        user = self.partner_id.user_ids[0]

        # 🔥 Your fork: writing 'password' is the correct way
        user.sudo().write({"password": self.new_password})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Success",
                "message": f"Password updated for {self.partner_id.name}",
                "type": "success",
                "sticky": False,
            },
        }
