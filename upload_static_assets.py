"""Use this to upload static content to S3."""

import flask_s3
from search.factory import create_ui_web_app

app = create_ui_web_app()

flask_s3.create_all(app, filepath_filter_regex=r"(base|css|images|js|sass)")
