"""Responsible for transforming metadata & fulltext into a search document."""

from datetime import datetime
from typing import Optional
from search.domain import Document, DocMeta, Fulltext


def _reformatDate(datestring: str,
                  output_format: str = '%Y-%m-%dT%H:%M:%S%z') -> str:
    """Recast DocMeta date format to ES date format."""
    try:
        asdate = datetime.strptime(datestring, '%Y-%m-%dT%H:%M:%S%z')
    except ValueError:
        return
    return asdate.strftime(output_format)


def _prepareSubmitter(meta: DocMeta) -> dict:
    return meta['submitter']


def _constructPubDate(meta: DocMeta) -> list:
    previous_versions = meta.get('previous_versions', [])
    current = _reformatDate(meta['modtime'])
    previous = [_reformatDate(v['modtime']) for v in previous_versions]
    # TODO: comparison should probably be done on datetime objects, not strings
    # now that dates are no longer YYMMDD
    previous = list(filter(lambda o: o is not None, previous))
    return list(sorted([current] + previous))[::-1]


def _constructPaperVersion(meta: DocMeta) -> str:
    """Generate a version-qualified paper ID."""
    if 'v' in meta['paper_id']:
        return meta['paper_id']
    return '%sv%i' % (meta['paper_id'], meta.get('version', 1))


def _constructMSCClass(meta: DocMeta) -> dict:
    """Extract ``msc_class`` field as an array."""
    raw = meta.get('msc_class')
    if not raw:
        return
    return [obj.strip() for obj in raw.split(',')]


def _constructACMClass(meta: DocMeta) -> dict:
    """Extract ``acm_class`` field as an array."""
    raw = meta.get('acm_class')
    if not raw:
        return
    return [obj.strip() for obj in raw.split(';')]


_transformations = [
    ('abstract', 'abstract'),
    ('authors', "authors_parsed"),
    ('authors_freeform', "authors_utf8"),
    ("author_owners", "author_owners"),
    ("created_date", lambda meta: _reformatDate(meta['created'])),
    ("publication_date", _constructPubDate),
    ("publication_date_first", lambda meta: _constructPubDate(meta)[-1]),
    ("publication_date_latest", lambda meta: _reformatDate(meta['modtime'])),
    ("updated_date", lambda meta: _reformatDate(meta['updated'])),
    ("is_current", "is_current"),
    ("is_withdrawn", "is_withdrawn"),
    ("license", "license"),
    ('paper_id', 'paper_id'),
    ('paper_id_v', _constructPaperVersion),
    ("primary_classification", "primary_classification"),
    ("secondary_classification", "secondary_classification"),
    ("title", "title"),
    ("source", "source"),
    ("version", "version"),
    ("submitter", _prepareSubmitter),
    ("report_num", "report_num"),
    ("proxy", "proxy"),
    ("msc_class", _constructMSCClass),
    ("metadata_id", "metadata_id"),
    ("journal_ref", "journal_ref_utf8"),
    ("is_withdrawn", "is_withdrawn"),
    ("is_current", "is_current"),
    ("doi", "doi"),
    ("comments", "comments_utf8"),
    ("acm_class", _constructACMClass),
    ("abs_categories", "abs_categories"),
    ("formats", "formats")
]

# TODO: it would be nice if we didn't need this.
_required = [
    "abstract",
    "authors",
    "date_created",
    "date_modified",
    "date_updated",
    "is_current",
    "is_withdrawn",
    "license",
    "paper_id",
    "paper_id_v",
    "primary_category",
    "primary_archive",
    "primary_group",
    "title",
    "source",
    "version"
]


def to_search_document(metadata: DocMeta, fulltext: Optional[Fulltext] = None)\
        -> Document:
    """
    Transform metadata (and fulltext) into a valid search document.

    Parameters
    ----------
    metadata : :class:`.DocMeta`
    fulltext : :class:`.Fulltext`

    Returns
    -------
    :class:`.Document`

    Raises
    ------
    ValueError
    """
    document = Document()
    for key, source in _transformations:
        if isinstance(source, str):
            value = metadata.get(source)
        elif hasattr(source, '__call__'):
            value = source(metadata)
        if not value and key not in _required:
            continue
        document[key] = value
    if fulltext:
        document['fulltext'] = fulltext.get('content', '')
    return document
