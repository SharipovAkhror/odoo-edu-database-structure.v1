from odoo import api, fields, models
from odoo.exceptions import UserError


import logging
_logger = logging.getLogger(__name__)

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
    
    
    def is_locked_for(self, user):
        self.ensure_one()
        return not self.can_access_for(user)
    
    def can_access_for(self, user):
        self.ensure_one()

        # Always allow officers
        if user.has_group('website_slides.group_website_slides_officer'):
            return True

        # Public users: keep accessible (change to False if you want lock for public too)
        if user._is_public():
            return True

        # ALWAYS define prev_slide
        prev_slide = self.env['slide.slide'].sudo().search([
            ('channel_id', '=', self.channel_id.id),
            ('sequence', '<', self.sequence),
            ('website_published', '=', True),
        ], order="sequence desc, id desc", limit=1)

        # First slide
        if not prev_slide:
            return True

        # Homeworks of previous slide
        published_homeworks = self.env['edu.homework'].sudo().search([
            ('slide_id', '=', prev_slide.id),
            ('is_published', '=', True),
        ])

        # STRICT (recommended for “turn by turn”):
        # if previous slide has no homework => lock next slide
        if not published_homeworks:
            return False

        # Must have at least one graded submission for previous slide homeworks
        passed = self.env['edu.homework.submission'].sudo().search_count([
            ('homework_id', 'in', published_homeworks.ids),
            ('user_id', '=', user.id),
            ('state', '=', 'graded'),
        ]) > 0

        return passed
