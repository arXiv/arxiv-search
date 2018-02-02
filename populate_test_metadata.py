"""Use this to populate a search index for testing."""

import json
import os
import click
from search.factory import create_web_app
from search.services import index, metadata
from search.process import transform

app = create_web_app()
app.app_context().push()


@app.cli.command()
@click.option('--print_indexable', '-i', is_flag=True,
              help='Print the indexable JSON to stdout.')
@click.option('--paper_id', '-p',
              help='Index specified paper id')
def populate(print_indexable, paper_id):
    """Populate the search index with some test data."""
    # Create cache directory if it doesn't exist
    cache_path_tmpl = 'tests/data/temp/%s.json'
    cache_dir = os.path.dirname(cache_path_tmpl)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    with open('tests/data/sample.json') as f:
        TO_INDEX = json.load(f).get('sample')

    if paper_id:
        TO_INDEX = [{'id': paper_id}]
    for doc in TO_INDEX:
        # Look for a local copy first.
        cache_path = cache_path_tmpl % doc['id'].replace('/', '_')
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                docmeta = json.load(f)
        else:
            # retrieve the metadata for the document
            docmeta = metadata.retrieve(doc['id'])
            with open(cache_path, 'w') as f:
                json.dump(docmeta, f)
        document = transform.to_search_document(docmeta)
        if print_indexable:
            print(document.json())
        index.add_document(document)

        click.echo(doc['id'])


if __name__ == '__main__':
    populate()
