/** @odoo-module **/

function getSlideId() {
    // Try data-slide-id on any element
    const el = document.querySelector("[data-slide-id]");
    if (el) {
        const v = el.getAttribute("data-slide-id");
        if (v) return v;
    }

    // Legacy global
    if (window.slide && window.slide.id) return String(window.slide.id);

    // Last number in URL: .../1-dars-20 -> 20
    const m = window.location.pathname.match(/(\d+)(?:\/)?$/);
    return m ? m[1] : null;
}

function ensureHomeworkTab() {
    try {
        // Try to find tab nav + content in regular lesson page
        const nav =
            document.querySelector(".o_wslides_lesson_nav") ||
            document.querySelector("ul.nav.nav-tabs");

        const content = document.querySelector(".tab-content");

        if (!nav || !content) return;

        // already added?
        if (nav.querySelector('[aria-controls="homeworks"]')) return;

        // Create tab button
        const li = document.createElement("li");
        li.className = "nav-item";

        const a = document.createElement("a");
        a.href = "#homeworks";
        a.className = "nav-link";
        a.setAttribute("data-bs-toggle", "tab");
        a.setAttribute("aria-controls", "homeworks");
        a.innerHTML = '<i class="fa fa-tasks"></i> Homeworks';

        li.appendChild(a);
        nav.appendChild(li);

        // Create panel
        const panel = document.createElement("div");
        panel.id = "homeworks";
        panel.className = "tab-pane pt-3";
        panel.innerHTML = '<p class="text-muted">Loading...</p>';

        content.appendChild(panel);

        const slideId = getSlideId();
        if (!slideId) {
            panel.innerHTML = '<p class="text-muted">No slide context.</p>';
            return;
        }

        // Fetch homeworks
        fetch(`/homework/slide/${slideId}/json`, { credentials: "same-origin" })
            .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
            .then((data) => {
                if (!Array.isArray(data) || data.length === 0) {
                    panel.innerHTML = '<p class="text-muted">No homeworks.</p>';
                    return;
                }

                const ul = document.createElement("ul");
                ul.className = "list-group";

                data.forEach((hw) => {
                    const item = document.createElement("li");
                    item.className = "list-group-item";

                    const link = document.createElement("a");
                    link.href = hw.url;
                    link.textContent = hw.name || "Homework";
                    item.appendChild(link);

                    if (hw.due_date) {
                        const br = document.createElement("br");
                        item.appendChild(br);

                        const small = document.createElement("small");
                        small.className = "text-muted";
                        small.textContent = `Due: ${hw.due_date}`;
                        item.appendChild(small);
                    }

                    ul.appendChild(item);
                });

                panel.innerHTML = "";
                panel.appendChild(ul);
            })
            .catch(() => {
                panel.innerHTML = '<p class="text-muted">Failed to load.</p>';
            });
    } catch (e) {
        console.error("Homework tab error", e);
    }
}

// Run on load + when Odoo updates DOM
function boot() {
    ensureHomeworkTab();
}

document.addEventListener("DOMContentLoaded", boot);
document.addEventListener("odoo:ready", boot);

// Handle dynamic page changes (slides / SPA-like behavior)
const obs = new MutationObserver(() => ensureHomeworkTab());
obs.observe(document.documentElement, { childList: true, subtree: true });
