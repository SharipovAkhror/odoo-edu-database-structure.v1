# -*- coding: utf-8 -*-
import base64
import mimetypes

from markupsafe import Markup, escape
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SlideSlide(models.Model):
    _inherit = "slide.slide"

    video_file = fields.Binary(
        string="Video File",
        attachment=True,
        help="Upload video file (MP4, WebM, OGG). Max size: 500MB",
    )
    video_filename = fields.Char("Video Filename")

    # Optional helper fields (keep if you want them in form)
    video_file_url = fields.Char(string="Video File URL", compute="_compute_video_file_url", store=True)
    video_file_url_preview = fields.Char(string="Video URL Preview", compute="_compute_video_file_url_preview")
    video_file_size = fields.Float(string="Video Size (MB)", compute="_compute_video_file_size", store=True)
    use_uploaded_video = fields.Boolean(string="Use Uploaded Video", compute="_compute_use_uploaded_video", store=True)

    @api.depends("video_file")
    def _compute_video_file_url(self):
        for slide in self:
            slide.video_file_url = f"/slides/video/stream/{slide.id}" if slide.video_file and slide.id else False

    @api.depends("video_file")
    def _compute_video_file_url_preview(self):
        for slide in self:
            if slide.video_file:
                slide.video_file_url_preview = f"/slides/video/stream/{slide.id}" if slide.id else \
                    "Will be generated after saving (e.g., /slides/video/stream/123)"
            else:
                slide.video_file_url_preview = False

    @api.depends("video_file")
    def _compute_video_file_size(self):
        for slide in self:
            if slide.video_file:
                try:
                    file_size_bytes = len(base64.b64decode(slide.video_file))
                    slide.video_file_size = round(file_size_bytes / (1024 * 1024), 2)
                except Exception:
                    slide.video_file_size = 0
            else:
                slide.video_file_size = 0

    @api.depends("video_file")
    def _compute_use_uploaded_video(self):
        for slide in self:
            slide.use_uploaded_video = bool(slide.video_file)

    @api.onchange("video_file")
    def _onchange_video_file(self):
        # avoid required field error
        if self.video_file and not self.video_url:
            self.video_url = "about:blank"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("video_file") and not vals.get("video_url"):
                vals["video_url"] = "about:blank"
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("video_file") and not vals.get("video_url"):
            if not self.video_url or self.video_url == "about:blank":
                vals["video_url"] = "about:blank"
        return super().write(vals)

    def _video_mime(self):
        self.ensure_one()
        return mimetypes.guess_type(self.video_filename or "")[0] or "video/mp4"

    # ✅ THIS IS THE IMPORTANT PART
    @api.depends("video_url", "slide_type", "video_file", "video_filename")
    def _compute_embed_code(self):
        # Let Odoo compute normal embed_code for YouTube/Vimeo links
        super()._compute_embed_code()

        # If uploaded video exists => override embed_code with HTML5 video
        for slide in self:
            if slide.slide_type == "video" and slide.video_file and slide.id:
                src = f"/slides/video/stream/{slide.id}"
                mime = slide._video_mime()

                slide.embed_code = Markup(f"""
                    <div class="ratio ratio-16x9">
                        <video class="w-100 h-100 ustudy-no-download-video"
                               controls
                               playsinline
                               controlsList="nodownload"
                               preload="metadata"
                               oncontextmenu="return false;"
                               style="background:#000; object-fit:contain;">
                            <source src="{escape(src)}" type="{escape(mime)}"/>
                        </video>
                    </div>
                """)

    @api.constrains("video_file", "video_filename")
    def _check_video_file(self):
        for slide in self:
            if not slide.video_file:
                continue

            # size validation
            try:
                file_size_bytes = len(base64.b64decode(slide.video_file))
            except Exception:
                continue

            max_size = 500 * 1024 * 1024
            if file_size_bytes > max_size:
                raise ValidationError(
                    f"Video file size ({round(file_size_bytes / (1024 * 1024), 2)} MB) "
                    f"exceeds maximum allowed size (500 MB)."
                )

            # ext validation
            if slide.video_filename:
                allowed = [".mp4", ".webm", ".ogg", ".avi", ".mov", ".mkv"]
                ext = "." + slide.video_filename.split(".")[-1].lower()
                if ext not in allowed:
                    raise ValidationError(f"Invalid video format. Allowed: {', '.join(allowed)}")
