"""Use this to populate a search index for testing."""

import json
import os
import click
from search.factory import create_ui_web_app
from search.agent import MetadataRecordProcessor, DocumentFailed, \
    IndexingFailed

app = create_ui_web_app()
app.app_context().push()


@app.cli.command()
@click.option('--print_indexable', '-i', is_flag=True,
              help='Print the indexable JSON to stdout.')
@click.option('--paper_id', '-p',
              help='Index specified paper id')
def populate(print_indexable, paper_id):
    """Populate the search index with some test data."""
    # Create cache directory if it doesn't exist
    # cache_path_tmpl = 'tests/data/temp/%s.json'
    # cache_dir = os.path.dirname(cache_path_tmpl)
    cache_dir = os.path.abspath('tests/data/temp')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    with open('tests/data/sample.json') as f:
        TO_INDEX = json.load(f).get('sample')

    MAX_ERRORS = int(os.environ.get('MAX_ERRORS', 5))

    processor = MetadataRecordProcessor()
    processor.init_cache(cache_dir)

    error_count = 0
    index_count = 0
    if paper_id:
        TO_INDEX = [{'id': paper_id}]
    for doc in TO_INDEX:
        if error_count > MAX_ERRORS:
            click.echo('Too many failed documents; aborting.')
            return

        arxiv_id = doc.get('id')
        if 'v' in arxiv_id:
            arxiv_id = arxiv_id.split('v')[0]
        try:
            document = processor.index_paper(arxiv_id)
        except DocumentFailed:
            error_count += 1
        except IndexingFailed as e:
            click.echo('Indexing failed, aborting: %s' % str(e))

        if print_indexable:
            click.echo(document.json())
        index_count += 1
        click.echo(doc['id'])
    click.echo(f'Indexed {index_count} documents')


if __name__ == '__main__':
    populate()
