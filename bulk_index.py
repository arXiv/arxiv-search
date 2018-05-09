"""Use this to populate a search index for testing."""

import json
import os
import tempfile
import click
from itertools import islice, groupby
from typing import List
import re
from search.factory import create_ui_web_app
from search.agent import MetadataRecordProcessor, DocumentFailed, \
    IndexingFailed
from search.domain import asdict, DocMeta, Document
from search.services import metadata, index
from search.process import transform

app = create_ui_web_app()


@app.cli.command()
@click.option('--print_indexable', '-i', is_flag=True,
              help='Print the indexable JSON to stdout.')
@click.option('--paper_id', '-p',
              help='Index specified paper id')
@click.option('--id_list', '-l',
              help="Index paper IDs in a file (one ID per line)")
@click.option('--load-cache', '-d', is_flag=True,
              help="Install papers from a cache on disk. Note: this will"
                   " preempt checking for new versions of papers that are"
                   " in the cache.")
@click.option('--cache-dir', '-c', help="Specify the cache directory.")
def populate(print_indexable: bool, paper_id: str, id_list: str,
             load_cache: bool, cache_dir: str) -> None:
    """Populate the search index with some test data."""
    cache_dir = init_cache(cache_dir)
    index_count = 0
    if paper_id:    # Index a single paper.
        TO_INDEX = [paper_id]
    elif id_list:   # Index a list of papers.
        TO_INDEX = load_id_list(id_list)
    else:
        TO_INDEX = load_id_sample()
    approx_size = len(TO_INDEX)

    retrieve_chunk_size = 50
    index_chunk_size = 250
    chunk: List[str] = []
    meta: List[DocMeta] = []

    try:
        with click.progressbar(length=approx_size,
                               label='Papers indexed') as index_bar:
            last = len(TO_INDEX) - 1
            for i, paper_id in enumerate(TO_INDEX):
                if load_cache:
                    try:
                        meta += from_cache(cache_dir, paper_id)
                        continue
                    except RuntimeError as e:    # No document.
                        pass

                chunk.append(paper_id)
                if len(chunk) == retrieve_chunk_size or i == last:
                    try:
                        new_meta = metadata.bulk_retrieve(chunk)
                    except metadata.ConnectionFailed as e:  # Try again.
                        new_meta = metadata.bulk_retrieve(chunk)
                    # Add metadata to the cache.
                    key = lambda dm: dm.paper_id
                    new_meta_srt = sorted(new_meta, key=key)
                    for paper_id, grp in groupby(new_meta_srt, key):
                        to_cache(cache_dir, paper_id, [dm for dm in grp])
                    meta += new_meta
                    chunk = []

                # Index papers on a different chunk cycle, and at the very end.
                if len(meta) >= index_chunk_size or i == last:
                    # Transform to Document.
                    documents = [
                        transform.to_search_document(dm) for dm in meta
                    ]
                    # Add to index.
                    index.bulk_add_documents(documents)

                    if print_indexable:
                        for document in documents:
                            click.echo(json.dumps(asdict(document)))
                    index_count += len(documents)
                    meta = []
                    index_bar.update(i)

    except Exception as e:
        raise RuntimeError('Populate failed: %s' % str(e)) from e

    finally:
        click.echo(f"Indexed {index_count} documents in total")
        click.echo(f"Cache path: {cache_dir}; use `-c {cache_dir}` to reuse in"
                   f" subsequent calls")


def init_cache(cache_dir: str) -> None:
    """Configure the processor to use a local cache for docmeta."""
    # Create cache directory if it doesn't exist
    if not (cache_dir and os.path.exists(cache_dir)
            and os.access(cache_dir, os.W_OK)):
        cache_dir = tempfile.mkdtemp()
    return cache_dir


def from_cache(cache_dir: str, arxiv_id: str) -> List[DocMeta]:
    """
    Get the docmeta document from a local cache, if available.

    Parameters
    ----------
    arxiv_id : str

    Returns
    -------
    :class:`.DocMeta`

    Raises
    ------
    RuntimeError
        Raised when the cache is not available, or the document could not
        be found in the cache.

    """
    fname = '%s.json' % arxiv_id.replace('/', '_')
    cache_path = os.path.join(cache_dir, fname)
    if not os.path.exists(cache_path):
        raise RuntimeError('No cached document')

    with open(cache_path) as f:
        data: dict = json.load(f)
        return [DocMeta(**datum) for datum in data]  # type: ignore
        # See https://github.com/python/mypy/issues/3937


def to_cache(cache_dir: str, arxiv_id: str, docmeta: List[DocMeta]) -> None:
    """
    Add a document to the local cache, if available.

    Parameters
    ----------
    arxiv_id : str
    docmeta : :class:`.DocMeta`

    Raises
    ------
    RuntimeError
        Raised when the cache is not available, or the document could not
        be added to the cache.

    """
    fname = '%s.json' % arxiv_id.replace('/', '_')
    cache_path = os.path.join(cache_dir, fname)
    try:
        with open(cache_path, 'w') as f:
            json.dump([asdict(dm) for dm in docmeta], f)
    except Exception as e:
        raise RuntimeError(str(e)) from e


def load_id_list(path: str) -> List[str]:
    """Load a list of paper IDs from ``path``."""
    if not os.path.exists(path):
        raise RuntimeError('Path does not exist: %s' % path)
        return
    with open(path) as f:
        # Stream from the file, in case it's large.
        return [ident.strip() for ident in f]


def load_id_sample() -> List[str]:
    """Load a list of IDs from the testing sample."""
    with open('tests/data/sample.json') as f:
        return [datum['id'] for datum in json.load(f).get('sample')]


if __name__ == '__main__':
    populate()
