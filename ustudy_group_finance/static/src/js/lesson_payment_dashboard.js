/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

export class LessonPaymentDashboardController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");

        this.dashboardData = useState({
            total_paid: "0",
            paid_lessons: 0,
            debt_lessons: 0,
            payment_foizi: "0%",
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    async loadDashboard() {
        const student_id = this.props.context.default_student_id || false;

        try {
            const data = await this.orm.call(
                "edu.student.lesson.payment.report",
                "get_payment_dashboard",
                [student_id]
            );

            this.dashboardData.total_paid = data.total_paid || "0";
            this.dashboardData.paid_lessons = data.paid_lessons || 0;
            this.dashboardData.debt_lessons = data.debt_lessons || 0;
            this.dashboardData.payment_foizi = data.payment_foizi || "0%";
        } catch (error) {
            console.error("Error loading payment dashboard:", error);
        }
    }
}

export const LessonPaymentDashboardListView = {
    ...listView,
    Controller: LessonPaymentDashboardController,
};

registry.category("views").add("lesson_payment_dashboard_list", LessonPaymentDashboardListView);
