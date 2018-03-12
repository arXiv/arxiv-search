"""Use this to populate a search index for testing."""

import json
import os
import click
import re
from search.factory import create_ui_web_app
from search.agent import MetadataRecordProcessor, DocumentFailed, \
    IndexingFailed
from search.domain import asdict

app = create_ui_web_app()
app.app_context().push()


@app.cli.command()
@click.option('--print_indexable', '-i', is_flag=True,
              help='Print the indexable JSON to stdout.')
@click.option('--paper_id', '-p',
              help='Index specified paper id')
@click.option('--id_list', '-l',
              help="Index paper IDs in a file (one ID per line)")
def populate(print_indexable, paper_id, id_list):
    """Populate the search index with some test data."""
    # Create cache directory if it doesn't exist
    cache_dir = os.path.abspath('tests/data/temp')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    MAX_ERRORS = int(os.environ.get('MAX_ERRORS', 5))

    processor = MetadataRecordProcessor()
    processor.init_cache(cache_dir)

    error_count = 0
    index_count = 0
    if paper_id:    # Index a single paper.
        TO_INDEX = [{'id': paper_id}]
    elif id_list:   # Index a list of papers.
        if not os.path.exists(id_list):
            click.echo('Path does not exist: %s' % id_list)
            return
        with open(id_list) as f:
            TO_INDEX = [{'id': ident.strip()} for ident in f.read().split()]
    else:
        with open('tests/data/sample.json') as f:
            TO_INDEX = json.load(f).get('sample')
    for doc in TO_INDEX:
        if error_count > MAX_ERRORS:
            click.echo('Too many failed documents; aborting.')
            return

        arxiv_id = doc.get('id')
        m = re.search(r'^(.*)(v[\d]+)?$', arxiv_id)
        arxiv_id = m.group(0)
        try:
            document = processor.index_paper(arxiv_id)
        except DocumentFailed:
            error_count += 1
        except IndexingFailed as e:
            click.echo('Indexing failed, aborting: %s' % str(e))
            return

        if print_indexable:
            click.echo(json.dumps(asdict(document)))
        index_count += 1
        click.echo(doc['id'])
    click.echo(f'Indexed {index_count} documents')


if __name__ == '__main__':
    populate()
