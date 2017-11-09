"""Use this to initialize the search index for testing."""

import json
import click
from search.factory import create_web_app
from search.services import index

app = create_web_app()
app.app_context().push()


@app.cli.command()
def create_index():
    """Initialize the search index."""
    with open('mappings/DocumentMapping.json') as f:
        mappings = json.load(f)
    index.current_session().create_index(mappings)


if __name__ == '__main__':
    create_index()
