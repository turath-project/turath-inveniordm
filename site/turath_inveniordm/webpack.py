from invenio_assets.webpack import WebpackThemeBundle
import os


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

previewer = WebpackThemeBundle(
    __name__,
    os.path.join(project_root, 'assets'),
    default='js/app.js',
    dependencies={
        "react": "16.14.0",
        "react-dom": "16.14.0",
        "prop-types": "^15.8.1",
        "invenio-previewer": "2.2.1",
    },
)

mirador_theme = WebpackThemeBundle(
    __name__,
    '/Users/paska/Invenio/invenio-previewer-mirador/invenio_previewer_mirador/assets',
    default='js/MiradorPreviewer.js',
    dependencies={
        "mirador": "3.2.0",
    },
)
