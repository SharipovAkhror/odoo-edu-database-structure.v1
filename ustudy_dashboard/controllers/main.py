# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class ElearningDashboardController(http.Controller):

    @http.route("/elearning/admin/dashboard/data", type="json", auth="user")
    def get_dashboard_data(self):
        dashboard_model = request.env["elearning.dashboard"]
        return dashboard_model.sudo().get_dashboard_data()
