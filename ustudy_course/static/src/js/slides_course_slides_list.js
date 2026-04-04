import publicWidget from "@web/legacy/js/public/public_widget";
import "@website_slides/js/slides_course_slides_list";

publicWidget.registry.websiteSlidesCourseSlidesList.include({
    _updateHref: function () {
        // Do not append fullscreen=1 to slide links
    }
});