"""
Run :mod:`arxiv.base.app_tests`.

These are run separately from the rest of the tests in :mod:`search`.
"""

import unittest
from search.factory import create_ui_web_app
from arxiv.base.app_tests import *

app = create_ui_web_app()
app.app_context().push()

if __name__ == '__main__':
    unittest.main()
