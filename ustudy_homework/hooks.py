def post_init_set_pass_ball(cr, registry):
    cr.execute("""
        UPDATE slide_channel
           SET homework_pass_mark = 75
         WHERE homework_pass_mark IS NULL OR homework_pass_mark = 0
    """)
