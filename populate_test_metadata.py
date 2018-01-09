"""Use this to populate a search index for testing."""

import json
import os
import click
from search.factory import create_web_app
from search.services import index, metadata
from search.process import transform

app = create_web_app()
app.app_context().push()

with open('tests/data/sample.json') as f:
    TO_INDEX = json.load(f).get('sample')


@app.cli.command()
def populate():
    """Populate the search index with some test data."""
    for doc in TO_INDEX:
        # Look for a local copy first.
        cache_path = 'tests/data/temp/%s.json' % doc['id'].replace('/', '_')
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                docmeta = json.load(f)
        else:
            docmeta = metadata.retrieve(doc['id'])
            with open(cache_path, 'w') as f:
                json.dump(docmeta, f)
        document = transform.to_search_document(docmeta)
        index.add_document(document)

        click.echo(doc['id'])


if __name__ == '__main__':
    populate()
