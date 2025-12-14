from odoo import fields, models


class SlideChannelPartner(models.Model):
    _inherit = "slide.channel.partner"

    edu_group_id = fields.Many2one(
        "edu.group",
        string="Group",
        ondelete="set null",
    )