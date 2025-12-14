{
    "name": "UStudy eLearning Homework",
    "version": "1.0.0",
    "summary": "Homework & grading for eLearning lessons",
    "category": "Education",
    "author": "Shohjahon Obruyev",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "mail",
        "website",
        "hr", 
        "website_slides",
        "ustudy_course",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/edu_homework_views.xml",
        "views/website_homework_templates.xml",
        # "views/website_slide_lock.xml",
        "views/slide_inherit_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ustudy_homework/static/src/js/ustudy_homework_tab.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
