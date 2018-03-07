"""Responsible for transforming metadata & fulltext into a search document."""

from datetime import datetime
from string import punctuation
from typing import Callable, Dict, List, Optional, Tuple, Union
from search.domain import Document, DocMeta, Fulltext


DEFAULT_LICENSE = {
    'uri': 'http://arxiv.org/licenses/assumed-1991-2003/',
    'label': "Assumed arXiv.org perpetual, non-exclusive license to distribute"
             " this article for submissions made before January 2004"
}


def _constructLicense(meta: DocMeta) -> dict:
    """Get the document license, or set the default."""
    if 'license' not in meta or not meta['license'] \
            or not meta['license']['uri']:
        return DEFAULT_LICENSE
    return meta['license']


def _strip_punctuation(s):
    return ''.join([c for c in s if c not in punctuation])


def _constructPaperVersion(meta: DocMeta) -> str:
    """Generate a version-qualified paper ID."""
    if 'v' in meta['paper_id']:
        return meta['paper_id']
    return '%sv%i' % (meta['paper_id'], meta.get('version', 1))


def _constructMSCClass(meta: DocMeta) -> list:
    """Extract ``msc_class`` field as an array."""
    if 'msc_class' not in meta or not meta['msc_class']:
        return None
    return [obj.strip() for obj in meta['msc_class'].split(',')]


def _constructACMClass(meta: DocMeta) -> list:
    """Extract ``acm_class`` field as an array."""
    if 'acm_class' not in meta or not meta['acm_class']:
        return None
    return [obj.strip() for obj in meta['acm_class'].split(';')]


def _transformAuthor(author: dict) -> dict:
    fname = _strip_punctuation(author['first_name'])
    author['initials'] = [pt[0] for pt in fname.split() if pt]
    author['full_name'] = f"{author['first_name']} {author['last_name']}"
    return author


def _constructAuthors(meta: DocMeta) -> List[Dict]:
    return [_transformAuthor(author)
            for author in meta.get("authors_parsed", [])]


def _constructAuthorOwners(meta: DocMeta) -> List[Dict]:
    return [_transformAuthor(author)
            for author in meta.get("author_owners", [])]


def _getFirstSubDate(meta: DocMeta) -> Optional[str]:
    if 'submitted_date_all' not in meta or not meta['submitted_date_all']:
        return None
    return meta['submitted_date_all'][0]


def _getLastSubDate(meta: DocMeta) -> Optional[str]:
    if 'submitted_date_all' not in meta or not meta['submitted_date_all']:
        return None
    return meta['submitted_date_all'][-1]


TransformType = Union[str, Callable]
_transformations: List[Tuple[str, TransformType]] = [
    ('id', 'paper_id'),
    ('abstract', 'abstract'),
    ('authors', _constructAuthors),
    ('authors_freeform', "authors_utf8"),
    ("owners", _constructAuthorOwners),
    ("submitted_date", "submitted_date"),
    ("submitted_date_all",
     lambda meta: meta.get('submitted_date_all', [])
     if meta.get('is_current') else None),
    ("submitted_date_first", _getFirstSubDate),
    ("submitted_date_latest", _getLastSubDate),
    ("modified_date", "modified_date"),
    ("updated_date", "updated_date"),
    ("announced_date_first", "announced_date_first"),
    ("is_current", "is_current"),
    ("is_withdrawn", "is_withdrawn"),
    ("license", _constructLicense),
    ('paper_id', 'paper_id'),
    ('paper_id_v', _constructPaperVersion),
    ("primary_classification", "primary_classification"),
    ("secondary_classification", "secondary_classification"),
    ("title", "title"),
    ("title_utf8", "title_utf8"),
    ("source", "source"),
    ("version", "version"),
    ("submitter", "submitter"),
    ("report_num", "report_num"),
    ("proxy", "proxy"),
    ("msc_class", _constructMSCClass),
    ("metadata_id", "metadata_id"),
    ("journal_ref", "journal_ref_utf8"),
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
