from odoo import models, fields, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    finance_count = fields.Integer(
        string="Payments",
        compute="_compute_finance_count"
    )

    def _compute_finance_count(self):
        payment_type = self.env['cc.payment.type'].search([
            ('code', '=', 'student_module'),
            ('type_category', '=', 'student')
        ], limit=1)

        for partner in self:
            domain = [("partner_id", "=", partner.id)]
            if payment_type:
                domain.append(("payment_type_id", "=", payment_type.id))

            partner.finance_count = self.env["cc.finance"].search_count(domain)


    def action_view_partner_finances(self):
        self.ensure_one()

        view_id = self.env.ref(
            "ustudy_group_finance.view_cc_finance_student_module_list"
        ).id

        payment_type = self.env['cc.payment.type'].search([
            ('code', '=', 'student_module'),
            ('type_category', '=', 'student')
        ], limit=1)

        domain = [("partner_id", "=", self.id)]
        if payment_type:
            domain.append(("payment_type_id", "=", payment_type.id))

        return {
            "name": _("Student Module Payments"),
            "type": "ir.actions.act_window",
            "res_model": "cc.finance",
            "view_mode": "list,form",
            "views": [(view_id, "list"), (False, "form")],
            "domain": domain,
            "context": {"default_partner_id": self.id},
        }
