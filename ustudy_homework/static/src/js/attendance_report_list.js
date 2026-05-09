/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

export class AttendanceReportDashboardController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");

        this.dashboardData = useState({
            present: 0,
            absent: 0,
            davomat_foizi: "0%",
            isAttendance: true,
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        const student_id = this.props.context.default_student_id || false;

        try {
            const data = await this.orm.call(
                "edu.student.lesson.report",
                "get_attendance_dashboard",
                [student_id]
            );

            this.dashboardData.present = data.present || 0;
            this.dashboardData.absent = data.absent || 0;
            this.dashboardData.davomat_foizi = data.davomat_foizi || "0%";
        } catch (error) {
            console.error("Error loading attendance dashboard:", error);
        }
    }
}

export const AttendanceReportListView = {
    ...listView,
    Controller: AttendanceReportDashboardController,
};

registry.category("views").add("attendance_report_dashboard_list", AttendanceReportListView);
