# models/notebook.py
from odoo import api, fields, models, _

class EduNotebook(models.Model):
    _name = "edu.notebook"
    _description = "Education Notebook (Laptop)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Notebook Number", required=True, tracking=True)
    image_1920 = fields.Image(max_width=1920, max_height=1920)
    model_name = fields.Char(string="Model Name")
    cpu = fields.Char(string="CPU")
    ram = fields.Char(string="OZU (RAM)")
    ssd = fields.Char(string="SSD")

    date_created = fields.Date(string="Date Created", tracking=True)
    daily_price = fields.Monetary(string="Daily Price", required=True, default=0.0)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id)
    serial_number = fields.Char(string="Serial Number", readonly=True, copy=False, index=True)

    borrow_ids = fields.One2many("edu.notebook.borrow", "notebook_id", string="Borrowings")
    last_user_id = fields.Many2one("res.partner", string="Last User", tracking=True)

    # NEW: status
    borrow_status = fields.Selection(
        [("available", "Free"), ("borrowed", "Ijarada")],
        compute="_compute_borrow_state",
        store=False,
        tracking=True,
        string="Status",
    )

    # keep boolean if you want it for modifiers (optional but convenient)
    is_borrowed = fields.Boolean(compute="_compute_borrow_state")
    current_borrow_id = fields.Many2one("edu.notebook.borrow", compute="_compute_borrow_state")

    current_student_id = fields.Many2one(related="current_borrow_id.student_id", readonly=True)
    current_start_datetime = fields.Datetime(related="current_borrow_id.start_datetime", readonly=True)
    current_return_datetime = fields.Datetime(related="current_borrow_id.return_datetime", readonly=True)

    borrow_count = fields.Integer(compute="_compute_borrow_count")

    _sql_constraints = [
        ("serial_number_unique", "unique(serial_number)", "Serial number must be unique."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("serial_number"):
                vals["serial_number"] = seq.next_by_code("edu.notebook.serial") or _("New")
            if not vals.get("name"):
                vals["name"] = vals["serial_number"]
        return super().create(vals_list)

    def _compute_borrow_count(self):
        for nb in self:
            nb.borrow_count = len(nb.borrow_ids)

    @api.depends("borrow_ids.state", "borrow_ids.start_datetime", "borrow_ids.return_datetime")
    def _compute_borrow_state(self):
        Borrow = self.env["edu.notebook.borrow"]

        # defaults
        for nb in self:
            nb.is_borrowed = False
            nb.borrow_status = "available"
            nb.current_borrow_id = False

        if not self.ids:
            return

        active_borrows = Borrow.search([
            ("notebook_id", "in", self.ids),
            ("state", "=", "active"),
        ], order="id desc")

        seen = set()
        for b in active_borrows:
            nid = b.notebook_id.id
            if nid in seen:
                continue
            seen.add(nid)
            nb = b.notebook_id
            nb.current_borrow_id = b
            nb.is_borrowed = True
            nb.borrow_status = "borrowed"

    def action_open_borrows(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Borrowings",
            "res_model": "edu.notebook.borrow",
            "view_mode": "list,form",
            "domain": [("notebook_id", "=", self.id)],
            "context": {"default_notebook_id": self.id},
        }
