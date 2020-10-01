"""Use this to populate a search index for testing."""

import os
import json
import tempfile
import operator

from datetime import datetime
from typing import List, Optional
from itertools import groupby

import click

from search.process import transform
from search.domain import asdict, DocMeta, Fulltext
from search.services import metadata, index
from search.factory import create_ui_web_app


app = create_ui_web_app()

get_paper_id = operator.attrgetter("paper_id")

# TODO: replace with real code
def get_full_text(file_name: str) -> Optional[Fulltext]:
    file_path = f'tests/data/articleTextOut/{file_name}.txt'
    if not os.path.exists(file_path):
        print(f'Full text not found: {file_name}')
        return None
    else:
        print(f'Found: {file_name}')
        with open(file_path , 'r') as file:
            data = file.read()
            return Fulltext(content=data, version="0.0.1-pre0", created=datetime.now())

@app.cli.command()
@click.option(
    "--print_indexable",
    "-i",
    is_flag=True,
    help="Index to ES and print the indexable JSON to stdout.",
)
@click.option("--paper_id", "-p", help="Index specified paper id")
@click.option(
    "--id_list", "-l", help="Index paper IDs in a file (one ID per line)"
)
@click.option("--cache-dir", "-c", help="Specify the cache directory."
              " Install papers from a cache on disk. Note: this will"
              " preempt checking for new versions of papers that are"
              " in the cache.")
@click.option("--no-cache", help="Disable the cache feature",
              is_flag=True, default=False)
@click.option("--quiet", "-q", help="Only print on failure",
              is_flag=True, default=False)
def populate(
    print_indexable: bool,
    paper_id: str,
    id_list: str,
    cache_dir: str,
    no_cache: bool,
    quiet: bool,
) -> None:
    """Populate the search index with some test data."""
    if cache_dir and no_cache:
        raise RuntimeError("Cannot set both no cache and cache dir")

    if not no_cache:
        cache_dir = init_cache(cache_dir)
    else:
        cache_dir = None

    index_count = 0
    if paper_id:  # Index a single paper.
        TO_INDEX = [paper_id]
    elif id_list:  # Index a list of papers.
        TO_INDEX = load_id_list(id_list)
    else:
        TO_INDEX = load_id_sample()
    approx_size = len(TO_INDEX)

    retrieve_chunk_size = 50
    index_chunk_size = 250
    chunk: List[str] = []
    meta: List[DocMeta] = []
    index.SearchSession.create_index()
    progress = NoopContextManager() if quiet \
        else click.progressbar(length=approx_size)
    try:
        with progress as index_bar:
            last = len(TO_INDEX) - 1
            for i, paper_id in enumerate(TO_INDEX):
                this_meta = []
                if cache_dir:
                    this_meta = from_cache(cache_dir, paper_id)

                if this_meta:
                    meta += this_meta
                else:
                    chunk.append(paper_id)

                if len(chunk) == retrieve_chunk_size or (chunk and i == last):
                    try:
                        new_meta = metadata.bulk_retrieve(chunk)
                    except metadata.ConnectionFailed:  # Try again.
                        new_meta = metadata.bulk_retrieve(chunk)

                    meta += new_meta
                    chunk = []
                    if not no_cache:
                        # Add metadata to the cache.
                        new_meta_srt = sorted(new_meta, key=get_paper_id)
                        for paper_id, grp in groupby(new_meta_srt, get_paper_id):
                            to_cache(cache_dir, paper_id, [dm for dm in grp])

                # Index papers on a different chunk cycle, and at the very end.
                if len(meta) >= index_chunk_size or i == last:
                    # Transform to Document.
                    docs = [
                        transform.to_search_document(dm, get_full_text(transform.constructPaperVersion(dm))) \
                        for dm in meta
                    ]
                    # Add to index.
                    index.SearchSession.bulk_add_documents(docs)

                    if print_indexable:
                        for document in docs:
                            click.echo(json.dumps(asdict(docs)))
                    index_count += len(docs)
                    meta = []
                    index_bar.update(i)
    finally:
        if not quiet:
            click.echo(f"Indexed {index_count} documents in total")
            if cache_dir:
                click.echo(
                    f"Cache path: {cache_dir}; use `-c {cache_dir}` to reuse in"
                    f" subsequent calls")


def init_cache(cache_dir: str) -> None:
    """Configure the processor to use a local cache for docmeta."""
    # Create cache directory if it doesn't exist
    if not (
        cache_dir
        and os.path.exists(cache_dir)
        and os.access(cache_dir, os.W_OK)
    ):
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
    :class:`.DocMeta` or None if document is not found in cache    

    """
    try:
        if not cache_dir:
            return [] # caching is disabled
        fname = "%s.json" % arxiv_id.replace("/", "_")
        cache_path = os.path.join(cache_dir, fname)
        if not os.path.exists(cache_path):
            raise RuntimeError("No cached document")

        with open(cache_path) as f:
            data: dict = json.load(f)
            return [DocMeta(**datum) for datum in data]  # type: ignore
            # See https://github.com/python/mypy/issues/3937
    except RuntimeError:
        return []


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
    if not cache_dir:
        return
    fname = "%s.json" % arxiv_id.replace("/", "_")
    cache_path = os.path.join(cache_dir, fname)
    try:
        with open(cache_path, "w") as f:
            json.dump([asdict(dm) for dm in docmeta], f)
    except Exception as ex:
        raise RuntimeError(str(ex)) from ex


def load_id_list(path: str) -> List[str]:
    """Load a list of paper IDs from ``path``."""
    if not os.path.exists(path):
        raise RuntimeError("Path does not exist: %s" % path)
        return
    with open(path) as f:
        # Stream from the file, in case it's large.
        return [ident.strip() for ident in f]


def load_id_sample() -> List[str]:
    """Load a list of IDs from the testing sample."""
    with open("tests/data/sample.json") as f:
        return [datum["id"] for datum in json.load(f).get("sample")]


class NoopContextManager(object):
    """Context manager that does nothing to replace click progressbar in
    quiet mode."""
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def update(self, i):
        pass


if __name__ == "__main__":
    populate()
