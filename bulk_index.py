"""Use this to populate a search index in bulk or prefetch metadata."""

import os
import click
from search.factory import create_ui_web_app
from search.agent import MetadataRecordProcessor, DocumentFailed, \
    IndexingFailed

app = create_ui_web_app()
app.app_context().push()


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


@app.cli.command()
@click.option('--paper_id', '-p',
              help='Index specified paper id')
@click.option('--id_list', '-l',
              help="Index paper IDs in a file (one ID per line)")
@click.option('--alt_cache_dir', '-c',
              help="Specify alternate cache directory for document metadata")
@click.option('--prefetch_metadata', '-m', is_flag=True,
              help="Prefetch latest version document metadata, don't index")
@click.option('--no_index', '-n', is_flag=True,
              help="Don't index; use with --prefetch_metadata")
def populate(paper_id, id_list, alt_cache_dir, prefetch_metadata, no_index):
    """Populate the search index with some test data."""
    cache_dir = os.path.abspath('tests/data/temp')
    # Create default cache directory if it doesn't exist
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    if alt_cache_dir:
        if not (os.path.exists and os.access(alt_cache_dir, os.W_OK)):
            click.echo(
                f'Path does not exist or is not writable: {alt_cache_dir}')
            return
        cache_dir = alt_cache_dir

    PAPERS_PER_BULK = 500
    MAX_ERRORS = int(os.environ.get('MAX_ERRORS', 5))

    processor = MetadataRecordProcessor()
    processor.init_cache(cache_dir)

    error_count = 0
    index_count = 0

    if paper_id:    # Index a single paper.
        TO_INDEX = [paper_id]
    elif id_list:   # Index a list of papers.
        if not os.path.exists(id_list):
            click.echo('Path does not exist: %s' % id_list)
            return
        with open(id_list) as f:
            TO_INDEX = [ident.strip() for ident in f.read().split()]

    docs = []
    for arxiv_id in TO_INDEX:
        if 'v' in arxiv_id:
            arxiv_id = arxiv_id.split('v')[0]
        docs.append(arxiv_id)

    # TODO: currently only works for latest version
    # TODO: lower McCabe index
    if prefetch_metadata:
        click.echo(f'Prefetching metdata for {len(docs)} papers...')
        with click.progressbar(length=len(docs),
                               label='Metadata fetched') as metadata_bar:
            try:
                for arxiv_id in docs:
                    if error_count >= MAX_ERRORS:
                        click.echo('Too many errors fetching '
                                   'metadata. Aborting.')
                        return
                    metadata_bar.update(1)
                    processor._get_metadata(arxiv_id)
            except DocumentFailed:
                error_count += 1
        if no_index:
            return

    click.echo(f'Indexing {len(docs)} papers...')
    with click.progressbar(length=len(docs),
                           label='Papers indexed') as index_bar:
        num_chunks = 0
        for chunk in chunks(docs, PAPERS_PER_BULK):
            try:
                num_chunks += 1
                processor.index_papers(chunk)
                index_count += len(chunk)
                index_bar.update(len(chunk))
            except DocumentFailed:
                error_count += 1
            except IndexingFailed as e:
                click.echo('Indexing failed, aborting: %s' % str(e))
                return
        click.echo(f'\nDone indexing {index_count} papers.')


if __name__ == '__main__':
    populate()
