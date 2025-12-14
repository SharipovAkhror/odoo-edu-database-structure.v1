from odoo import api, fields, models
from odoo.exceptions import UserError


class SlideSlide(models.Model):
    _inherit = "slide.slide"

    homework_ids = fields.One2many('edu.homework', 'slide_id', string='Homeworks')
    homework_count = fields.Integer(string='Homeworks', compute='_compute_homework_count')

    @api.depends('homework_ids')
    def _compute_homework_count(self):
        for rec in self:
            rec.homework_count = len(rec.homework_ids)

    def get_my_homework_mark(self):
        """Return latest graded mark for this slide for current user (or False)."""
        self.ensure_one()
        user = self.env.user
        if user._is_public():
            return False

        Submission = self.env['edu.homework.submission'].sudo()
        sub = Submission.search([
            ('homework_id.slide_id', '=', self.id),
            ('user_id', '=', user.id),
            ('mark', '!=', False),
        ], order="submit_date desc", limit=1)

        return sub.mark if sub else False

    def can_access_for(self, user):
        """Return True if this slide is accessible for given user."""
        self.ensure_one()

        # Let admins / managers in always
        if user.has_group('website_slides.group_website_slides_officer'):
            return True

        # First slide in channel? always open
        prev_slide = self.env['slide.slide'].sudo().search([
            ('channel_id', '=', self.channel_id.id),
            ('sequence', '<', self.sequence),
        ], order="sequence desc, id desc", limit=1)

        if not prev_slide:
            return True

        # If previous slide has no published homework → open
        published_homeworks = prev_slide.homework_ids.filtered(lambda h: h.is_published)
        if not published_homeworks:
            return True

        # Check if user has any submission for those homeworks
        Submission = self.env['edu.homework.submission'].sudo()
        sub = Submission.search([
            ('homework_id', 'in', published_homeworks.ids),
            ('user_id', '=', user.id),
        ], limit=1)

        return bool(sub)