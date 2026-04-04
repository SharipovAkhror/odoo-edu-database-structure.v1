/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { onMounted } from "@odoo/owl";

patch(FormRenderer.prototype, {

    setup() {
        super.setup();

        onMounted(() => {
            this._setupChatterToggle();
        });
    },

    _setupChatterToggle() {
        const chatter = this.el.querySelector(".o_ChatterContainer");
        if (!chatter) {
            return;
        }

        // Hide chatter by default
        chatter.classList.add("d-none");

        // Prevent duplicate button
        if (this.el.querySelector(".o_toggle_chatter_btn")) {
            return;
        }

        // Create button
        const button = document.createElement("button");
        button.innerText = "Toggle Chatter";
        button.type = "button";
        button.className = "btn btn-secondary mb-2 o_toggle_chatter_btn";

        button.addEventListener("click", () => {
            chatter.classList.toggle("d-none");
        });

        // Insert button before form sheet
        const sheet = this.el.querySelector(".o_form_sheet_bg");
        if (sheet) {
            sheet.prepend(button);
        }
    },
});