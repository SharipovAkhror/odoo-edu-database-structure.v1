# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides


class WebsiteSlidesLock(WebsiteSlides):
    # IMPORTANT: do NOT add @http.route() here.
    # We only override the method, Odoo keeps the original route.

    def slide_view(self, slide, **kwargs):
        if slide and not slide.can_access_for(request.env.user):
            return request.redirect(slide.channel_id.website_url)
        return super().slide_view(slide, **kwargs)
