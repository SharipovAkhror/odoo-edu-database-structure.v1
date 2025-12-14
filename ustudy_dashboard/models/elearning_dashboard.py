# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, timedelta
import json


class ElearningDashboard(models.Model):
    _name = "elearning.dashboard"
    _description = "uStudy eLearning Admin Dashboard"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    dashboard_data = fields.Text(
        string="Dashboard Data",
        readonly=True,
        compute="_compute_dashboard_data",
    )

    def _get_date_range(self):
        today = fields.Date.context_today(self)
        start = today - timedelta(days=29)
        return start, today

    @api.depends("company_id")
    def _compute_dashboard_data(self):
        SlideChannelPartner = self.env["slide.channel.partner"].sudo()
        SlideChannel = self.env["slide.channel"].sudo()
        PaymentTransaction = self.env["payment.transaction"].sudo()

        for rec in self:
            start_date, end_date = rec._get_date_range()

            # --- KPI-lar ---

            # 1) Total students (unique partners with at least 1 enrollment)
            students_rg = SlideChannelPartner.read_group(
                domain=[],
                fields=["partner_id"],
                groupby=["partner_id"],
            )
            total_students = len(students_rg)

            # 2) Active courses
            total_courses = SlideChannel.search_count([("is_published", "=", True)])

            # 3) Avg completion (maydon bo'lmasa ham yiqilmasin)
            completion_rg = SlideChannelPartner.read_group(
                domain=[("completion", ">", 0)],
                fields=["completion:avg"],
                groupby=[],
            )
            if completion_rg:
                avg_completion = float(completion_rg[0].get("completion_avg") or 0.0)
            else:
                avg_completion = 0.0

            # 4) Monthly revenue (last 30 days)
            monthly_rev_domain = [
                ("state", "=", "done"),
                ("create_date", ">=", datetime.combine(start_date, datetime.min.time())),
                ("create_date", "<=", datetime.combine(end_date, datetime.max.time())),
            ]
            revenue_rg = PaymentTransaction.read_group(
                domain=monthly_rev_domain,
                fields=["amount:sum"],
                groupby=[],
            )
            if revenue_rg:
                monthly_revenue = float(revenue_rg[0].get("amount_sum") or 0.0)
            else:
                monthly_revenue = 0.0

            # --- Charts data ---

            # Enrollments per day (last 30 days)
            enrollments_by_day = []
            enrollments_rg = SlideChannelPartner.read_group(
                domain=[
                    ("create_date", ">=", datetime.combine(start_date, datetime.min.time())),
                    ("create_date", "<=", datetime.combine(end_date, datetime.max.time())),
                ],
                fields=["id"],
                groupby=["create_date:day"],
                orderby="create_date:day",
            )
            for r in enrollments_rg:
                enrollments_by_day.append({
                    "date": r.get("create_date:day") or r.get("create_date_day") or "",
                    "count": r.get("create_date:day_count") or r.get("create_date_day_count") or 0,
                })

            # Students per course (top 8)
            students_by_course = []
            course_rg = SlideChannelPartner.read_group(
                domain=[],
                fields=["id"],
                groupby=["channel_id"],
                orderby="channel_id_count desc",
                limit=8,
            )
            for r in course_rg:
                channel_id = r.get("channel_id") and r["channel_id"][0]
                channel = SlideChannel.browse(channel_id) if channel_id else False
                students_by_course.append({
                    "course": channel.name if channel else "N/A",
                    "students": r.get("channel_id_count") or 0,
                })

            # Avg progress per course (top 8)
            avg_progress_by_course = []
            progress_rg = SlideChannelPartner.read_group(
                domain=[("completion", ">", 0)],
                fields=["completion:avg"],
                groupby=["channel_id"],
            )

            # Python'da sort qilamiz (completion_avg bo'yicha, kamayish tartibida)
            progress_sorted = sorted(
                progress_rg,
                key=lambda r: float(r.get("completion_avg") or 0.0),
                reverse=True,
            )[:8]

            avg_progress_by_course = []
            for r in progress_sorted:
                channel_id = r.get("channel_id") and r["channel_id"][0]
                channel = SlideChannel.browse(channel_id) if channel_id else False
                avg_progress_by_course.append({
                    "course": channel.name if channel else "N/A",
                    "avg_progress": float(r.get("completion_avg") or 0.0),
                })

            # Revenue by month (last 12 months)
            revenue_by_month = []
            rev_rg = PaymentTransaction.read_group(
                domain=[("state", "=", "done")],
                fields=["amount:sum"],
                groupby=["create_date:month"],
                orderby="create_date:month",
                limit=12,
            )
            for r in rev_rg:
                revenue_by_month.append({
                    "month": r.get("create_date:month") or r.get("create_date_month") or "",
                    "amount": float(r.get("amount_sum") or 0.0),
                })

            payload = {
                "kpis": {
                    "total_students": total_students,
                    "total_courses": total_courses,
                    "avg_completion": round(avg_completion or 0.0, 1),
                    "monthly_revenue": monthly_revenue,
                },
                "charts": {
                    "enrollments_by_day": enrollments_by_day,
                    "students_by_course": students_by_course,
                    "avg_progress_by_course": avg_progress_by_course,
                    "revenue_by_month": revenue_by_month,
                },
            }

            rec.dashboard_data = json.dumps(payload, default=str)
