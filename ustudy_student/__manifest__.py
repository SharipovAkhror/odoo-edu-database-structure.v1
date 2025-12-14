{
    "name": "Ustudy Students",
    "version": "1.0",
    "author": "Ustudy",
    "depends": [
        "contacts",        # res.partner
        "website_slides",  # eLearning
    ],
    "data": [
        "security/student_groups.xml",
        "wizards/student_password_wizard_view.xml",
        "security/ir.model.access.csv",

        "views/student_menu.xml",        # root + student list menu
        "views/cc_region_views.xml",     # region views + action + region menu
        "views/student_partner_form.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'ustudy_student/static/src/css/custom.css',
        ],
    },
    "application": True,
}