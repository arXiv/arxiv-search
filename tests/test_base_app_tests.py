"""Run :mod:`arxiv.base.app_tests`."""

import unittest
from search.factory import create_ui_web_app
from arxiv.base.app_tests import *

app = create_ui_web_app()
app.app_context().push()
