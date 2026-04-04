{
    "name": "Ustudy Course Builder",
    "version": "19.0.1.0.0",
    "summary": "Custom structure for eLearning: Module -> Lesson -> {video, files, homework}",
    "author": "Ustudy",
    "license": "LGPL-3",
    "depends": [
        "website_slides",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/elearning_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ustudy_course/static/src/js/slides_course_slides_list.js",
        ],
    },
    "installable": True,
    "application": False,
}