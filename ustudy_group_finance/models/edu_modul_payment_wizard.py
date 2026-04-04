# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EduModulePaymentWizard(models.TransientModel):
    _name = 'edu.module.payment.wizard'
    _description = 'Register Module Payment'

    student_line_id = fields.Many2one(
        'edu.group.student',
        string='Student',
        required=True
    )

    student_name = fields.Char(
        related='student_line_id.student_name',
        string='Student Name',
        readonly=True
    )

    group_name = fields.Char(
        related='student_line_id.group_id.name',
        string='Group',
        readonly=True
    )

    module_id = fields.Many2one(
        "edu.module",
        string="Module",
        required=True,
        readonly=True
    )

    module_number = fields.Integer(
        related="module_id.sequence",
        string="Module Number",
        readonly=True
    )

    amount = fields.Float(
        string='Amount',
        required=True
    )

    payment_method_id = fields.Many2one(
        'cc.payment.method',
        string='Payment Method',
        required=True
    )

    payment_date = fields.Date(
        string='Payment Date',
        default=fields.Date.context_today,
        required=True
    )

    is_full_payment = fields.Boolean(
        string='Mark as Fully Paid (Override)',
        default=False,
        help='Force mark module as fully paid even if amount is less than module price'
    )

    notes = fields.Text(string='Notes')

    current_paid = fields.Float(
        related='student_line_id.current_module_payment_amount',
        string='Already Paid',
        readonly=True
    )

    module_price = fields.Float(
        related='student_line_id.module_price',
        string='Module Price',
        readonly=True
    )

    # --------------------------
    # MODULE CHANGE PART
    # --------------------------
    update_module = fields.Boolean(
        string="Update Student Module",
        default=False
    )

    new_module_id = fields.Many2one(
        "edu.module",
        string="New Module"
    )

    @api.constrains("update_module", "new_module_id")
    def _check_new_module(self):
        for rec in self:
            if rec.update_module and not rec.new_module_id:
                raise ValidationError(_("Please select New Module."))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Default payment method = cash
        payment_method = self.env['cc.payment.method'].search([('code', '=', 'cash')], limit=1)
        if payment_method:
            res['payment_method_id'] = payment_method.id

        # Default module_id from student_line_id
        if res.get("student_line_id"):
            student_line = self.env["edu.group.student"].browse(res["student_line_id"])
            if student_line.current_module_id:
                res["module_id"] = student_line.current_module_id.id

        return res

    def action_register_payment(self):
        """Register the module payment"""
        self.ensure_one()

        config = self.env['edu.config'].get_config()

        if not self.module_id:
            raise UserError(_("Module is not selected."))

        # Get or create payment type for student module payment
        payment_type = self.env['cc.payment.type'].search([
            ('code', '=', 'student_module'),
            ('type_category', '=', 'student')
        ], limit=1)

        if not payment_type:
            payment_type = self.env['cc.payment.type'].create({
                'name': 'Student Module Payment',
                'code': 'student_module',
                'type_category': 'student',
            })

        # Create finance record (INCOME - student paying to center)
        description_parts = [
            _('%s payment - %s') % (self.module_id.name, self.group_name)
        ]
        if self.notes:
            description_parts.append(self.notes)

        finance = self.env['cc.finance'].create({
            'date': self.payment_date,
            'transaction_type': 'income',
            'partner_id': self.student_line_id.student_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_type_id': payment_type.id,
            'amount': self.amount,
            'description': '\n'.join(description_parts),
            'state': 'draft',
        })

        finance.action_confirm()

        # Update student line payment fields
        new_payment_amount = self.student_line_id.current_module_payment_amount + self.amount

        vals = {
            'current_module_payment_amount': new_payment_amount,
        }

        # Mark as paid only if total amount >= module price OR admin explicitly overrides
        if new_payment_amount >= config.module_price or self.is_full_payment:
            vals['current_module_paid'] = True
            if self.student_line_id.state == 'frozen':
                vals['state'] = 'active'

        self.student_line_id.write(vals)

        # If user selected module update
        if self.update_module and self.new_module_id:
            self.student_line_id.write({
                "current_module_id": self.new_module_id.id,
                "lessons_in_current_module": 0,
                "current_module_paid": False,
                "current_module_payment_amount": 0.0,
            })

        # Post message to group
        message_parts = [
            _("💰 Module Payment Registered"),
            _("Student: %s") % self.student_line_id.student_id.name,
            _("Module: %s") % self.module_id.name,
            _("Amount: %s") % "{:,.2f}".format(self.amount),
            _("Total Paid: %s / %s") % (
                "{:,.2f}".format(new_payment_amount),
                "{:,.2f}".format(config.module_price)
            )
        ]

        if vals.get('current_module_paid'):
            message_parts.append(_("✅ Module fully paid"))
            if vals.get('state') == 'active':
                message_parts.append(_("🔓 Student unfrozen"))

        if self.update_module and self.new_module_id:
            message_parts.append(_("🔄 Module changed to: %s") % self.new_module_id.name)

        self.student_line_id.group_id.message_post(body='\n'.join(message_parts))

        return {'type': 'ir.actions.act_window_close'}
