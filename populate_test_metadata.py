"""Use this to populate a search index for testing."""

import json
import click
from search.factory import create_web_app
from search.services import index, metadata
from search import transform

app = create_web_app()
app.app_context().push()

with open('tests/data/to_index.json') as f:
    TO_INDEX = json.load(f).get('documents')


@app.cli.command()
def populate():
    """Populate the search index with some test data."""
    search = index.current_session()
    for document_id in TO_INDEX:
        document = transform.to_search_document(metadata.retrieve(document_id))
        search.add_document(document)
        click.echo(document_id)


if __name__ == '__main__':
    populate()
