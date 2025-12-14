/** @odoo-module **/

import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";

const { Component, useEffect, useState } = owl;

const CHART_JS_URL = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js";

export class ElearningDashboardWidget extends Component {
    static template = "custom.elearning_dashboard";

    setup() {
        // Dashboard data uchun lokal holat
        this.state = useState({ main_data: {} });

        // props.record yo'q bo'lsa ham yiqilmasin
        const getRawData = () => {
            const record = this.props && this.props.record;
            if (!record || !record.data) {
                return "{}";
            }
            return record.data.dashboard_data || "{}";
        };

        useEffect(
            () => {
                let parsed = {};
                try {
                    const raw = getRawData();
                    parsed = JSON.parse(raw || "{}");
                } catch (e) {
                    console.error("Invalid dashboard_data JSON", e);
                    parsed = {};
                }
                this.state.main_data = parsed;

                // Chart.js yuklab bo'lingandan keyin chizish
                loadJS(CHART_JS_URL)
                    .then(() => {
                        this.renderKPIs();
                        this.renderCharts();
                    })
                    .catch((err) => {
                        console.error("Chart.js load error", err);
                    });
            },
            // Dependensiya - dashboard_data o'zgarganda qayta ishga tushadi
            () => {
                const record = this.props && this.props.record;
                return [record && record.data && record.data.dashboard_data];
            }
        );
    }

    // --- KPI’lar matnlarini DOMga joylash ---
    renderKPIs() {
        const kpis = this.state.main_data.kpis || {};
        const setText = (id, v) => {
            const el = document.getElementById(id);
            if (el && v !== undefined && v !== null) {
                el.textContent = v;
            }
        };

        setText("kpi_total_students", kpis.total_students || 0);
        setText("kpi_total_courses", kpis.total_courses || 0);

        const avg = Number(kpis.avg_completion || 0);
        setText("kpi_avg_completion", avg.toFixed(1) + "%");

        const rev = Number(kpis.monthly_revenue || 0);
        setText("kpi_monthly_revenue", rev.toLocaleString());
    }

    renderCharts() {
        if (typeof Chart === "undefined") {
            console.warn("Chart.js is not loaded");
            return;
        }
        this.renderEnrollmentsByDay();
        this.renderStudentsByCourse();
        this.renderAvgProgressByCourse();
        this.renderRevenueByMonth();
    }

    _gradient(ctx, c1, c2, vertical = false) {
        const g = ctx.createLinearGradient(
            0,
            0,
            vertical ? 0 : ctx.canvas.width,
            vertical ? ctx.canvas.height : 0
        );
        g.addColorStop(0, c1);
        g.addColorStop(1, c2);
        return g;
    }

    // --- 1) Kunlik enrollments ---
    renderEnrollmentsByDay() {
        const canvas = document.getElementById("chart_enrollments_by_day");
        if (!canvas || typeof Chart === "undefined") return;
        const ctx = canvas.getContext("2d");

        const data = this.state.main_data.charts?.enrollments_by_day || [];
        const labels = data.map((d) => d.date || "");
        const values = data.map((d) => Number(d.count || 0));

        const gradient = this._gradient(ctx, "#38bdf8", "#6366f1", true);

        new Chart(ctx, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Enrollments",
                        data: values,
                        fill: true,
                        borderColor: "#38bdf8",
                        backgroundColor: gradient,
                        borderWidth: 2,
                        tension: 0.35,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#020617",
                        titleColor: "#f9fafb",
                        bodyColor: "#e5e7eb",
                        padding: 10,
                        cornerRadius: 8,
                    },
                },
                scales: {
                    x: {
                        ticks: { color: "#9ca3af", font: { size: 11 } },
                        grid: { color: "#111827" },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: "#9ca3af", font: { size: 11 } },
                        grid: { color: "#111827" },
                    },
                },
            },
        });
    }

    // --- 2) Students per course ---
    renderStudentsByCourse() {
        const canvas = document.getElementById("chart_students_by_course");
        if (!canvas || typeof Chart === "undefined") return;
        const ctx = canvas.getContext("2d");

        const data = this.state.main_data.charts?.students_by_course || [];
        const sorted = [...data].sort((a, b) => (b.students || 0) - (a.students || 0));
        const labels = sorted.map((d) => d.course || "");
        const values = sorted.map((d) => Number(d.students || 0));

        const gradient = this._gradient(ctx, "#f97316", "#ec4899");

        new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Students",
                        data: values,
                        backgroundColor: gradient,
                        borderRadius: 10,
                        borderSkipped: false,
                    },
                ],
            },
            options: {
                indexAxis: "y",
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#020617",
                        titleColor: "#f9fafb",
                        bodyColor: "#e5e7eb",
                        padding: 10,
                        cornerRadius: 8,
                    },
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: { color: "#9ca3af", font: { size: 11 } },
                        grid: { color: "#111827" },
                    },
                    y: {
                        ticks: { color: "#e5e7eb", font: { size: 11 } },
                        grid: { display: false },
                    },
                },
            },
        });
    }

    // --- 3) Avg progress per course ---
    renderAvgProgressByCourse() {
        const canvas = document.getElementById("chart_avg_progress_by_course");
        if (!canvas || typeof Chart === "undefined") return;
        const ctx = canvas.getContext("2d");

        const data = this.state.main_data.charts?.avg_progress_by_course || [];
        const labels = data.map((d) => d.course || "");
        const values = data.map((d) => Number(d.avg_progress || 0));

        const gradient = this._gradient(ctx, "#22c55e", "#14b8a6");

        new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Avg progress (%)",
                        data: values,
                        backgroundColor: gradient,
                        borderRadius: 8,
                        borderSkipped: false,
                    },
                ],
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#020617",
                        titleColor: "#f9fafb",
                        bodyColor: "#e5e7eb",
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: (ctx) => `${ctx.parsed.y.toFixed(1)}%`,
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: { color: "#e5e7eb", font: { size: 11 } },
                        grid: { display: false },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: "#9ca3af",
                            font: { size: 11 },
                            callback: (v) => `${v}%`,
                        },
                        grid: { color: "#111827" },
                    },
                },
            },
        });
    }

    // --- 4) Revenue by month ---
    renderRevenueByMonth() {
        const canvas = document.getElementById("chart_revenue_by_month");
        if (!canvas || typeof Chart === "undefined") return;
        const ctx = canvas.getContext("2d");

        const data = this.state.main_data.charts?.revenue_by_month || [];
        const labels = data.map((d) => d.month || "");
        const values = data.map((d) => Number(d.amount || 0));

        const gradient = this._gradient(ctx, "#eab308", "#f97316", true);

        new Chart(ctx, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Revenue",
                        data: values,
                        borderColor: "#f59e0b",
                        backgroundColor: gradient,
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#020617",
                        titleColor: "#f9fafb",
                        bodyColor: "#e5e7eb",
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: (ctx) => ctx.parsed.y.toLocaleString(),
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: { color: "#9ca3af", font: { size: 11 } },
                        grid: { color: "#111827" },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: "#9ca3af",
                            font: { size: 11 },
                            callback: (v) => v.toLocaleString(),
                        },
                        grid: { color: "#111827" },
                    },
                },
            },
        });
    }
}

// ⚠️ MUHIM: registry-ga TO‘G‘RI formatda qo‘shamiz
registry.category("fields").add("elearning_dashboard", {
    component: ElearningDashboardWidget,
});

export default ElearningDashboardWidget;
