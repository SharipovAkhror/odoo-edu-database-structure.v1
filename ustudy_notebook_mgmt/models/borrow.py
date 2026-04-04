from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class EduNotebookBorrow(models.Model):
    _name = "edu.notebook.borrow"
    _description = "Notebook Borrowing"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Borrow Ref", readonly=True, copy=False, default=lambda self: _("New"))

    notebook_id = fields.Many2one("edu.notebook", required=True, tracking=True)
    student_id = fields.Many2one(
        "res.partner", required=True, tracking=True,
        domain=[("is_company", "=", False)]
    )

    # datetime instead of date
    start_datetime = fields.Datetime(string="Start Date & Time", required=True, tracking=True, default=fields.Datetime.now)
    return_datetime = fields.Datetime(string="Return Date & Time", tracking=True, readonly=True)

    # pricing per hour (change label if you want per minute)
    hourly_price = fields.Monetary(string="Money per hour", required=True, default=0.0)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id)

    # duration in hours (can be fractional)
    duration_hours = fields.Float(string="Hours", compute="_compute_duration_hours", store=True, digits=(16, 2))
    total_amount = fields.Monetary(compute="_compute_total", store=True)

    state = fields.Selection([
        ("draft", "Draft"),
        ("active", "Borrowed"),
        ("returned", "Returned"),
        ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name") in (False, _("New"), "New"):
                vals["name"] = seq.next_by_code("edu.notebook.borrow") or _("BRW")
        return super().create(vals_list)

    @api.depends("start_datetime", "return_datetime", "state")
    def _compute_duration_hours(self):
        for r in self:
            if not r.start_datetime:
                r.duration_hours = 0.0
                continue

            # if returned, use stored return_datetime; if active, compute up to "now"
            end_dt = r.return_datetime or (fields.Datetime.now() if r.state == "active" else False)
            if not end_dt:
                r.duration_hours = 0.0
                continue

            start = fields.Datetime.to_datetime(r.start_datetime)
            end = fields.Datetime.to_datetime(end_dt)

            if end < start:
                r.duration_hours = 0.0
            else:
                seconds = (end - start).total_seconds()
                r.duration_hours = seconds / 3600.0

    @api.depends("duration_hours", "hourly_price")
    def _compute_total(self):
        for r in self:
            r.total_amount = r.duration_hours * r.hourly_price

    @api.constrains("notebook_id", "state")
    def _check_double_active(self):
        for r in self:
            if r.state == "active":
                other = self.search([
                    ("id", "!=", r.id),
                    ("notebook_id", "=", r.notebook_id.id),
                    ("state", "=", "active"),
                ], limit=1)
                if other:
                    raise ValidationError(_("This notebook is already borrowed (active)."))

    def action_confirm_borrow(self):
        self.write({"state": "active"})
        for r in self:
            if r.notebook_id and r.student_id:
                r.notebook_id.write({"last_user_id": r.student_id.id})
        self._refresh_notebook()

    def action_return(self):
        # auto-set return time at the moment of return
        now = fields.Datetime.now()
        self.write({"state": "returned", "return_datetime": now})
        for r in self:
            if r.notebook_id and r.student_id:
                r.notebook_id.write({"last_user_id": r.student_id.id})
        self._refresh_notebook()

    def _refresh_notebook(self):
        notebooks = self.mapped("notebook_id")
        notebooks.invalidate_recordset(["is_borrowed", "current_borrow_id"])

    def action_cancel(self):
        self.write({"state": "cancelled"})
