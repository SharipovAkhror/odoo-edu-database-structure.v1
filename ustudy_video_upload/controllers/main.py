# -*- coding: utf-8 -*-
import base64
import mimetypes
import os
import re

from odoo import http
from odoo.http import request, Response


class VideoStreamController(http.Controller):

    @http.route(
        "/slides/video/stream/<int:slide_id>",
        type="http",
        auth="public",
        website=True,
        csrf=False,
        sitemap=False,
        methods=["GET", "HEAD"],
    )
    def stream_video(self, slide_id, **kwargs):
        slide = request.env["slide.slide"].browse(slide_id)
        if not slide.exists():
            return request.not_found()

        # ✅ Access gate BEFORE sudo
        try:
            if hasattr(slide, "can_access_from_current_website") and not slide.can_access_from_current_website():
                return request.redirect("/web/login")
        except Exception:
            return request.redirect("/web/login")

        # ✅ IMPORTANT: public user can't read attachments => use sudo for attachment
        attachment = request.env["ir.attachment"].sudo().search([
            ("res_model", "=", "slide.slide"),
            ("res_id", "=", slide.id),
            ("res_field", "=", "video_file"),
        ], limit=1)

        if not attachment:
            return request.not_found()

        filename = attachment.name or slide.video_filename or "video.mp4"
        mime_type = mimetypes.guess_type(filename)[0] or "video/mp4"

        range_header = request.httprequest.headers.get("Range")

        def _headers(content_length=None, content_range=None):
            h = [
                ("Content-Type", mime_type),
                ("Accept-Ranges", "bytes"),
                ("Content-Disposition", "inline"),
                ("Cache-Control", "private, max-age=3600"),
                ("X-Content-Type-Options", "nosniff"),
            ]
            if content_length is not None:
                h.append(("Content-Length", str(content_length)))
            if content_range is not None:
                h.append(("Content-Range", content_range))
            return h

        # HEAD => headers only
        if request.httprequest.method == "HEAD":
            size = attachment.file_size or 0
            return Response(b"", status=200, headers=_headers(content_length=size))

        # --- A) Filestore streaming ---
        store_fname = getattr(attachment, "store_fname", None)
        if store_fname:
            try:
                full_path = attachment._full_path(store_fname)
            except Exception:
                full_path = None

            if full_path and os.path.exists(full_path):
                file_size = os.path.getsize(full_path)

                if range_header:
                    m = re.match(r"bytes=(\d+)-(\d*)", range_header.strip())
                    if not m:
                        return Response(status=416, headers=[("Accept-Ranges", "bytes")])

                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else file_size - 1

                    if start >= file_size or end < start:
                        return Response(
                            status=416,
                            headers=[
                                ("Content-Range", f"bytes */{file_size}"),
                                ("Accept-Ranges", "bytes"),
                            ],
                        )

                    end = min(end, file_size - 1)
                    length = end - start + 1

                    def file_iter(path, offset, count, chunk_size=1024 * 256):
                        with open(path, "rb") as f:
                            f.seek(offset)
                            remaining = count
                            while remaining > 0:
                                data = f.read(min(chunk_size, remaining))
                                if not data:
                                    break
                                remaining -= len(data)
                                yield data

                    return Response(
                        file_iter(full_path, start, length),
                        status=206,
                        headers=_headers(
                            content_length=length,
                            content_range=f"bytes {start}-{end}/{file_size}",
                        ),
                        direct_passthrough=True,
                    )

                def full_file_iter(path, chunk_size=1024 * 256):
                    with open(path, "rb") as f:
                        while True:
                            data = f.read(chunk_size)
                            if not data:
                                break
                            yield data

                return Response(
                    full_file_iter(full_path),
                    status=200,
                    headers=_headers(content_length=file_size),
                    direct_passthrough=True,
                )

        # --- B) DB base64 fallback ---
        if not attachment.datas:
            return request.not_found()

        try:
            video_data = base64.b64decode(attachment.datas)
        except Exception:
            return request.not_found()

        video_size = len(video_data)

        if range_header:
            m = re.match(r"bytes=(\d+)-(\d*)", range_header.strip())
            if not m:
                return Response(status=416, headers=[("Accept-Ranges", "bytes")])

            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else video_size - 1

            if start >= video_size or end < start:
                return Response(
                    status=416,
                    headers=[
                        ("Content-Range", f"bytes */{video_size}"),
                        ("Accept-Ranges", "bytes"),
                    ],
                )

            end = min(end, video_size - 1)
            chunk = video_data[start:end + 1]

            return Response(
                chunk,
                status=206,
                headers=_headers(
                    content_length=len(chunk),
                    content_range=f"bytes {start}-{end}/{video_size}",
                ),
            )

        return Response(video_data, status=200, headers=_headers(content_length=video_size))
