/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched, onWillStart, useState } from "@odoo/owl";

export class FinanceDashboardController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");

        this.dashboardData = useState({
            income: 0,
            expense: 0,
            balance: 0,
        });

        this._lastDomain = null;

        onWillStart(() => this._loadDashboard());
        onMounted(() => this._renderDashboard());
        onPatched(() => this._onPatched());
    }

    _getDomain() {
        try {
            return JSON.stringify(this.model.root.domain || []);
        } catch {
            return "[]";
        }
    }

    /**
     * Analyze active domain to build a human-readable label
     * e.g. "Fevral 2026", "2026 yil", "01.02 - 28.02", etc.
     */
    _getFilterLabel() {
        let domain = [];
        try {
            domain = this.model.root.domain || [];
        } catch {
            return _defaultLabel();
        }

        if (!domain.length) return _defaultLabel();

        // Flatten nested domains (AND/OR arrays)
        const conditions = _flattenDomain(domain);

        // Extract date conditions
        const dateGte = conditions.find(c => c[0] === 'date' && c[1] === '>=');
        const dateLte = conditions.find(c => c[0] === 'date' && c[1] === '<=');

        if (dateGte && dateLte) {
            const from = new Date(dateGte[2]);
            const to   = new Date(dateLte[2]);

            // Same month & year → "Fevral 2026"
            if (
                from.getFullYear() === to.getFullYear() &&
                from.getMonth()    === to.getMonth()
            ) {
                return _monthName(from);
            }

            // Same year, different months → "Yan - Mar 2026"
            if (from.getFullYear() === to.getFullYear()) {
                return `${_shortMonth(from)} - ${_shortMonth(to)} ${from.getFullYear()}`;
            }

            // Different years → show date range
            return `${_fmt(from)} - ${_fmt(to)}`;
        }

        if (dateGte) {
            const from = new Date(dateGte[2]);
            return `${_fmt(from)} dan`;
        }

        if (dateLte) {
            const to = new Date(dateLte[2]);
            return `${_fmt(to)} gacha`;
        }

        // Has other filters but no date filter
        return "Filtrlangan";
    }

    async _onPatched() {
        const currentDomain = this._getDomain();
        if (currentDomain !== this._lastDomain) {
            this._lastDomain = currentDomain;
            await this._loadDashboard();
        }
        this._renderDashboard();
    }

    async _loadDashboard() {
        let domain = [];
        try {
            domain = this.model.root.domain || [];
        } catch {
            domain = [];
        }

        try {
            const data = await this.orm.call("cc.finance", "get_finance_dashboard", [domain], {});
            this.dashboardData.income  = data.income  || 0;
            this.dashboardData.expense = data.expense || 0;
            this.dashboardData.balance = data.balance || 0;
        } catch (e) {
            console.error("Finance dashboard error:", e);
        }
    }

    _formatAmount(value) {
        return new Intl.NumberFormat('uz-UZ').format(Math.round(value));
    }

    _renderDashboard() {
        document.querySelectorAll(".o_finance_dashboard_banner").forEach(el => el.remove());

        const root = document.querySelector(".o_list_view");
        if (!root) return;

        const d = this.dashboardData;
        const label = this._getFilterLabel();
        const balanceColor = d.balance >= 0 ? "#1b5e20" : "#b71c1c";
        const balanceBg    = d.balance >= 0 ? "#e8f5e9"  : "#fdecea";

        const banner = document.createElement("div");
        banner.className = "o_finance_dashboard_banner d-flex gap-3 px-3 pt-3 pb-2";
        banner.innerHTML = `
            <div class="o_group_dashboard_card flex-fill" style="background:#e8f4fd;">
                <div class="o_group_dashboard_icon"><i class="fa fa-arrow-down" style="color:#1565c0;"></i></div>
                <div class="o_group_dashboard_info">
                    <div class="o_group_dashboard_value" style="color:#1565c0;">${this._formatAmount(d.income)}</div>
                    <div class="o_group_dashboard_label" style="color:#1565c0;">${label} kirim</div>
                </div>
            </div>
            <div class="o_group_dashboard_card flex-fill" style="background:#fdecea;">
                <div class="o_group_dashboard_icon"><i class="fa fa-arrow-up" style="color:#b71c1c;"></i></div>
                <div class="o_group_dashboard_info">
                    <div class="o_group_dashboard_value" style="color:#b71c1c;">${this._formatAmount(d.expense)}</div>
                    <div class="o_group_dashboard_label" style="color:#b71c1c;">${label} chiqim</div>
                </div>
            </div>
            <div class="o_group_dashboard_card flex-fill" style="background:${balanceBg};">
                <div class="o_group_dashboard_icon"><i class="fa fa-balance-scale" style="color:${balanceColor};"></i></div>
                <div class="o_group_dashboard_info">
                    <div class="o_group_dashboard_value" style="color:${balanceColor};">${this._formatAmount(d.balance)}</div>
                    <div class="o_group_dashboard_label" style="color:${balanceColor};">${label} balans</div>
                </div>
            </div>
        `;
        root.insertBefore(banner, root.firstChild);
    }
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function _defaultLabel() {
    const now = new Date();
    return _monthName(now);
}

function _monthName(date) {
    const MONTHS = [
        "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
        "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
    ];
    return `${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
}

function _shortMonth(date) {
    const MONTHS = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn",
                    "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"];
    return MONTHS[date.getMonth()];
}

function _fmt(date) {
    const d = String(date.getDate()).padStart(2, '0');
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const y = date.getFullYear();
    return `${d}.${m}.${y}`;
}

/**
 * Recursively flatten Odoo domain arrays into simple [field, op, value] triples.
 */
function _flattenDomain(domain) {
    const result = [];
    for (const item of domain) {
        if (Array.isArray(item)) {
            if (typeof item[0] === 'string') {
                // It's a leaf condition like ['date', '>=', '2026-02-01']
                result.push(item);
            } else {
                // It's a nested domain
                result.push(..._flattenDomain(item));
            }
        }
        // skip '&', '|', '!' operators
    }
    return result;
}

// ─── Registration ────────────────────────────────────────────────────────────

export const FinanceDashboardListView = {
    ...listView,
    Controller: FinanceDashboardController,
};

registry.category("views").add("finance_dashboard_list", FinanceDashboardListView);