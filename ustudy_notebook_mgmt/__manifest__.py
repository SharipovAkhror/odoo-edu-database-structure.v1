{
    "name": "Education Notebook Management",
    "version": "1.0",
    "category": "Education",
    "depends": ["base", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/notebook_views.xml",
        "views/borrow_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ustudy_notebook_mgmt/static/src/css/notebook_kanban.css",
        ],
    },
    "application": True,
}