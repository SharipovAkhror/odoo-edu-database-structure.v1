/** @odoo-module **/

/*
 UStudy Video Protection (Odoo 19 safe)
 - No legacy widgets
 - No dependency on web.public.widget
 - Works in minimal + fullscreen bundles
 - Pure DOM logic
*/

function protectVideos(root = document) {
    const videos = root.querySelectorAll("video.ustudy-no-download-video");

    videos.forEach((video) => {
        // Prevent right click
        video.addEventListener("contextmenu", (ev) => {
            ev.preventDefault();
            return false;
        });

        // Prevent common save shortcuts
        video.addEventListener("keydown", (ev) => {
            if ((ev.ctrlKey || ev.metaKey) && (ev.key === "s" || ev.key === "d")) {
                ev.preventDefault();
                return false;
            }
        });

        // Disable drag
        video.addEventListener("dragstart", (ev) => {
            ev.preventDefault();
            return false;
        });
    });
}

// Initial page load
document.addEventListener("DOMContentLoaded", () => protectVideos());

// Odoo frontend ready (SPA navigation / fullscreen)
document.addEventListener("odoo:ready", () => protectVideos());

// Observe dynamic DOM changes (fullscreen, slide navigation)
const observer = new MutationObserver(() => protectVideos());
observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
});
