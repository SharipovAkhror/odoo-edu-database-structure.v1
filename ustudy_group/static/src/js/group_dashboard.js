/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched, onWillStart, useState } from "@odoo/owl";

export class GroupDashboardController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dashboardData = useState({
            total: 0,
            active: 0,
            students: 0,
            active_students: 0,
        });

        onWillStart(() => this._loadDashboard());
        onMounted(() => this._renderDashboard());
        onPatched(() => this._renderDashboard());
    }

    async _loadDashboard() {
        const data = await this.orm.call("edu.group", "get_group_dashboard", [], {});
        console.log("Dashboard data:", data); // check browser console
        this.dashboardData.total           = data.total           || 0;
        this.dashboardData.active          = data.active          || 0;
        this.dashboardData.students        = data.students        || 0;
        this.dashboardData.active_students = data.active_students || 0;
    }

    _renderDashboard() {
        document.querySelectorAll(".o_group_dashboard_banner").forEach(el => el.remove());

        const root = document.querySelector(".o_list_view");
        if (!root) return;

        const d = this.dashboardData;
        const banner = document.createElement("div");
        banner.className = "o_group_dashboard_banner d-flex gap-3 px-3 pt-3 pb-2";
        banner.innerHTML = `
            <div class="o_group_dashboard_card o_group_dashboard_total flex-fill">
                <div class="o_group_dashboard_icon"><i class="fa fa-th-large"></i></div>
                <div class="o_group_dashboard_info">
                    <div class="o_group_dashboard_value">${d.total}</div>
                    <div class="o_group_dashboard_label">Jami guruhlar</div>
                </div>
            </div>
            <div class="o_group_dashboard_card o_group_dashboard_active flex-fill">
                <div class="o_group_dashboard_icon"><i class="fa fa-play-circle"></i></div>
                <div class="o_group_dashboard_info">
                    <div class="o_group_dashboard_value">${d.active}</div>
                    <div class="o_group_dashboard_label">Faol guruhlar</div>
                </div>
            </div>
            <div class="o_group_dashboard_card o_group_dashboard_students flex-fill">
                <div class="o_group_dashboard_icon"><i class="fa fa-users"></i></div>
                <div class="o_group_dashboard_info">
                    <div class="o_group_dashboard_value">${d.students}</div>
                    <div class="o_group_dashboard_label">Jami talabalar</div>
                </div>
            </div>
            <div class="o_group_dashboard_card o_group_dashboard_active_students flex-fill">
                <div class="o_group_dashboard_icon"><i class="fa fa-user"></i></div>
                <div class="o_group_dashboard_info">
                    <div class="o_group_dashboard_value">${d.active_students}</div>
                    <div class="o_group_dashboard_label">Faol talabalar</div>
                </div>
            </div>
        `;
        root.insertBefore(banner, root.firstChild);
    }
}

export const GroupDashboardListView = {
    ...listView,
    Controller: GroupDashboardController,
};

registry.category("views").add("group_dashboard_list", GroupDashboardListView);