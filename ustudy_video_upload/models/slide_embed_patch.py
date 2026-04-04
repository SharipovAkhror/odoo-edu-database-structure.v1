# -*- coding: utf-8 -*-
from odoo import api, models
from markupsafe import Markup, escape
import mimetypes

class SlideSlide(models.Model):
    _inherit = "slide.slide"

    def _ustudy_guess_mimetype(self):
        self.ensure_one()
        name = getattr(self, "video_filename", None) or ""
        return mimetypes.guess_type(name)[0] or "video/mp4"

    @api.depends("slide_type", "video_url", "video_file", "video_filename")
    def _compute_embed_code(self):
        # let Odoo compute embed_code normally first (youtube/vimeo/etc.)
        super()._compute_embed_code()

        for slide in self:
            if slide.slide_type != "video":
                continue

            if slide.video_file and slide.id:
                src = f"/slides/video/stream/{slide.id}"
                mime = slide._ustudy_guess_mimetype()

                # IMPORTANT: put the <video> inside embed_code so all existing templates work
                slide.embed_code = Markup(
                    f"""
                    <div class="ratio ratio-16x9">
                        <video class="w-100 h-100 ustudy-no-download-video"
                               controls playsinline preload="metadata"
                               controlsList="nodownload"
                               oncontextmenu="return false;">
                            <source src="{escape(src)}" type="{escape(mime)}"/>
                        </video>
                    </div>
                    """
                )
