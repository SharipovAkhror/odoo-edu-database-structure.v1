/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

export class LessonReportDashboardController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");

        this.dashboardData = useState({
            total: 0,
            present: 0,
            obs: 0,
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        if (this.props.resModel !== 'edu.student.lesson.report') {
            return;
        }

        const student_id = this.props.context.default_student_id || false;

        try {
            const data = await this.orm.call(
                "edu.student.lesson.report",
                "get_attendance_dashboard",
                [student_id]
            );

            this.dashboardData.total = data.total || 0;
            this.dashboardData.present = data.present || 0;
            this.dashboardData.obs = data.obs || 0;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        }
    }
}

export const LessonReportDashboardListView = {
    ...listView,
    Controller: LessonReportDashboardController,
};

registry.category("views").add("lesson_report_dashboard_list", LessonReportDashboardListView);