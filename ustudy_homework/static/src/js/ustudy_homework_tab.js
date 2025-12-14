odoo.define('ustudy_homework.add_tab', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.EduHomeworkTab = publicWidget.Widget.extend({
        selector: 'body',

        start: function () {
            this._super.apply(this, arguments);
            this._addTab();
        },

        _getSlideId: function () {
            const c = $('[data-slide-id]').first();
            if (c.length) return c.data('slide-id');

            if (window.slide && window.slide.id) return window.slide.id;

            // take the last number in the path (…/1-dars-20 -> 20)
            const m = window.location.pathname.match(/(\d+)(?:\/)?$/);
            if (m) return m[1];

            return null;
        },

        _addTab: function () {
            try {
                const $nav = $('.o_wslides_lesson_nav, ul.nav.nav-tabs').first();
                const $content = $('.tab-content').first();

                if (!$nav.length || !$content.length) return;
                if ($nav.find('[aria-controls="homeworks"]').length) return;

                const $li = $('<li/>', {class: 'nav-item'});
                const $a = $('<a/>', {
                    href: '#homeworks',
                    class: 'nav-link',
                    'data-bs-toggle': 'tab',
                    'aria-controls': 'homeworks',
                }).html('<i class="fa fa-tasks"></i> Homeworks');

                $li.append($a);
                $nav.append($li);

                const $panel = $('<div/>', {
                    id: 'homeworks',
                    class: 'tab-pane pt-3',
                }).html('<p class="text-muted">Loading...</p>');

                $content.append($panel);

                const slideId = this._getSlideId();
                if (!slideId) {
                    $panel.html('<p class="text-muted">No slide context.</p>');
                    return;
                }

                $.get(`/homework/slide/${slideId}/json`).then(function (data) {
                    if (!data.length) {
                        $panel.html('<p class="text-muted">No homeworks.</p>');
                        return;
                    }

                    const $ul = $('<ul/>', {class: 'list-group'});

                    data.forEach(hw => {
                        const $item = $('<li/>', {class: 'list-group-item'});
                        $item.append(`<a href="${hw.url}">${hw.name}</a>`);
                        if (hw.due_date)
                            $item.append(`<br><small class="text-muted">Due: ${hw.due_date}</small>`);

                        $ul.append($item);
                    });

                    $panel.empty().append($ul);
                }).fail(() => {
                    $panel.html('<p class="text-muted">Failed to load.</p>');
                });

            } catch (e) {
                console.error('Homework tab error', e);
            }
        }
    });
});
