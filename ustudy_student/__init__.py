from . import models
from . import wizards


def post_init_hook(env):
    """Create missing edu.course records and sync names from slide.channel."""
    channels = env["slide.channel"].with_context(active_test=False).search([])
    EduCourse = env["edu.course"].with_context(active_test=False)
    for channel in channels:
        course = EduCourse.search([("slide_channel_id", "=", channel.id)], limit=1)
        if not course:
            EduCourse.create({
                "name": channel.name,
                "slide_channel_id": channel.id,
                "is_published": channel.is_published,
                "company_id": channel.company_id.id or env.company.id,
            })
        elif course.name != channel.name:
            course.name = channel.name