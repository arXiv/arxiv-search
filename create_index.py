"""Use this to initialize the search index for testing."""

import json
import click
from search.factory import create_ui_web_app
from search.services import index

app = create_ui_web_app()
app.app_context().push()


@app.cli.command()
def create_index():
    """Initialize the search index."""
    index.SearchSession.create_index()


if __name__ == '__main__':
    create_index()
