odoo.define("ustudy_homework.lesson_calendar", function (require) {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        const el = document.getElementById("lesson_calendar");
        if (!el) {
            return;
        }

        let events = el.dataset.events;
        if (!events) {
            el.innerHTML = "<p class='text-danger'>No events found</p>";
            return;
        }

        try {
            events = JSON.parse(events);
        } catch (e) {
            el.innerHTML = "<p class='text-danger'>Calendar data error</p>";
            return;
        }

        if (!events.length) {
            el.innerHTML = "<p class='text-muted'>Hozircha darslar mavjud emas.</p>";
            return;
        }

        let html = "<ul class='list-group'>";

        events.forEach(ev => {
            html += `
                <li class="list-group-item">
                    <b>${ev.timetable_name || "-"}</b><br/>
                    <small>${ev.start_datetime || ""}</small>
                </li>
            `;
        });

        html += "</ul>";

        el.innerHTML = html;
    });
});
