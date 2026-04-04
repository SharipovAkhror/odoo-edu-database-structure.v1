{
    'name': 'UStudy Video Upload',
    'version': '1.0.0',
    'category': 'Education',
    'summary': 'Upload video files directly to eLearning slides',
    'description': """
        UStudy Video Upload
        ===================
        * Upload video files (MP4, WebM, OGG) instead of video links
        * Custom video player with controls
        * File size validation
        * Support for multiple video formats
    """,
    'author': 'Shohjahon Obruyev',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'website_slides',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/slide_inherit_views.xml',
        'views/website_video_player.xml',
        'views/website_fullscreen.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'ustudy_video_upload/static/src/css/video_player.css',
            'ustudy_video_upload/static/src/js/video_player.js',
        ],
        'web.assets_frontend_minimal': [
            'ustudy_video_upload/static/src/css/video_player.css',
            'ustudy_video_upload/static/src/css/ustudy_slides_fullwidth.css',
            'ustudy_video_upload/static/src/js/video_player.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
