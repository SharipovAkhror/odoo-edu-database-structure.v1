# ustudy_student/models/res_partner.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    # --- Student flag & relations (your existing code) -----------------------
    is_student = fields.Boolean(
        string="Is Student",
        help="If checked, this contact is considered a student.",
    )
    birth_date = fields.Date(string="Birth Date")

    slide_channel_partner_ids = fields.One2many(
        "slide.channel.partner",
        "partner_id",
        string="Kurslar (eLearning)",
    )

    enrollment_ids = fields.One2many(
        "edu.enrollment",
        "student_id",
        string="Course Enrollments",
    )

    total_courses = fields.Integer(
        string="Total Courses",
        compute="_compute_student_stats",
        store=False,
    )
    avg_progress = fields.Float(
        string="Average Progress (%)",
        compute="_compute_student_stats",
        store=False,
    )
    avg_mark = fields.Float(
        string="Average Mark",
        compute="_compute_student_stats",
        store=False,
    )
    
    cc_region_id = fields.Many2one(
        "cc.region",
        string="Tuman",
        domain="[('state_id', '=', state_id)]",
    )

    # --- Address tweak: default country = Uzbekistan ------------------------
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        default=lambda self: self.env.ref(
            "base.uz", raise_if_not_found=False
        ) or self.env.company.country_id,
    )

    # --- Extra docs (passport etc.) ----------------------------------------
    passport_number = fields.Char(string="Passport Number")
    passport_file = fields.Binary(string="Passport Scan")
    passport_filename = fields.Char(string="Passport File Name")

    extra_doc_name = fields.Char(string="Extra Document Name")
    extra_doc_file = fields.Binary(string="Extra Document")
    extra_doc_filename = fields.Char(string="Extra Document File Name")

    # ---------------------------------------------------------------------
    # STATS
    # ---------------------------------------------------------------------
    @api.depends("enrollment_ids.progress")
    def _compute_student_stats(self):
        for partner in self:
            enrollments = partner.enrollment_ids
            partner.total_courses = len(enrollments)
            partner.avg_progress = (
                sum(e.progress for e in enrollments) / len(enrollments)
            ) if enrollments else 0.0
            partner.avg_mark = 0.0  # placeholder

    # ---------------------------------------------------------------------
    # STUDENT PORTAL ACCESS (your existing method, untouched)
    # ---------------------------------------------------------------------
    def action_grant_portal_access(self):
        self.ensure_one()

        if not self.is_student:
            raise UserError(_("Only students can be granted portal access."))

        if not self.email:
            raise UserError(
                _("Student '%s' must have an email to grant portal access.")
                % self.display_name
            )

        if self.user_ids:
            raise UserError(
                _("Student '%s' already has a user account.")
                % self.display_name
            )

        Users = self.env["res.users"]
        user_fields = Users._fields

        vals = {
            "name": self.name or self.display_name,
            "login": self.email,
            "email": self.email,
            "partner_id": self.id,
            "share": True,
        }

        PORTAL_FIELD = "edu_role_portal"
        USER_FIELD = "edu_role_user"
        ADMIN_FIELD = "edu_role_admin"
        STUDENT_FIELD = "edu_student"

        if PORTAL_FIELD in user_fields:
            vals[PORTAL_FIELD] = True
        if USER_FIELD in user_fields:
            vals[USER_FIELD] = False
        if ADMIN_FIELD in user_fields:
            vals[ADMIN_FIELD] = False
        if STUDENT_FIELD in user_fields:
            vals[STUDENT_FIELD] = True

        Users.create(vals)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Portal user created for %s") % self.display_name,
                "type": "success",
                "sticky": False,
            },
        }
        
        
    @api.onchange('state_id')
    def _onchange_state_id(self):
        # if you already override this in another module, merge logic
        if self.cc_region_id and self.cc_region_id.state_id != self.state_id:
            self.cc_region_id = False