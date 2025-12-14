# -*- coding: utf-8 -*-
{
    "name": "uStudy eLearning Dashboard",
    "version": "1.0",
    "summary": "Interactive admin dashboard for uStudy eLearning",
    "description": """
        eLearning Admin Dashboard
        =========================
        * Students, courses, progress and revenue
        * Charts for enrollments and course performance
    """,
    "author": "Shohjahon Obruyev",
    "website": "",
    "category": "Productivity",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "website_slides",  # Odoo eLearning
        "payment",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/elearning_dashboard_view.xml",
        "views/elearning_dashboard_menu.xml",
    ],
    "images": ["static/icon.png"],
    "assets": {
        "web.assets_backend": [
            # Chart.js CDN (xuddi DrukSmart kabi tashqaridan yuklash)
            "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js",
            # Dashboard JS/CSS/XML
            "ustudy_dashboard/static/src/js/*.js",
            "ustudy_dashboard/static/src/scss/*.scss",
            "ustudy_dashboard/static/src/xml/*.xml",
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
