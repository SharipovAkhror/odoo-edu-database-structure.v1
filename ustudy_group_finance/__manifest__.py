# -*- coding: utf-8 -*-
{
    "name": "UStudy Group Finance Connector",
    "version": "19.0.1.0.0",
    "category": "Education",
    "summary": "Connect Education Groups with Finance (Student Payments, Smart Buttons, Wizards)",
    "author": "Shohjahon Obruyev",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "contacts",
        "hr",
        "ustudy_group",   # Education core
        "edu_finance",     # Finance core
    ],
    "data": [
        "security/ir.model.access.csv",

        # Wizards
        "views/edu_payment_wizard_views.xml",

        # Smart buttons / student finance view
        "views/edu_group_student_finance_views.xml",

    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
