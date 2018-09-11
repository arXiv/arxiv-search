"""Responsible for transforming metadata & fulltext into a search document."""

from string import punctuation
import re
from typing import Callable, Dict, List, Optional, Tuple, Union
from search.domain import Document, DocMeta, Fulltext

DEFAULT_LICENSE = {
    'uri': 'http://arxiv.org/licenses/assumed-1991-2003/',
    'label': "Assumed arXiv.org perpetual, non-exclusive license to distribute"
             " this article for submissions made before January 2004"
}


def _constructLicense(meta: DocMeta) -> dict:
    """Get the document license, or set the default."""
    if not meta.license or not meta.license['uri']:
        return DEFAULT_LICENSE
    return meta.license


def _strip_punctuation(s: str) -> str:
    return ''.join([c for c in s if c not in punctuation])


def _constructPaperVersion(meta: DocMeta) -> str:
    """Generate a version-qualified paper ID."""
    return '%sv%i' % (meta.paper_id, meta.version)


def _constructMSCClass(meta: DocMeta) -> Optional[list]:
    """Extract ``msc_class`` field as an array."""
    if not meta.msc_class:
        return None
    return [obj.strip() for obj in meta.msc_class.split(',')]


def _constructACMClass(meta: DocMeta) -> Optional[list]:
    """Extract ``acm_class`` field as an array."""
    if not meta.acm_class:
        return None
    return [obj.strip() for obj in meta.acm_class.split(';')]


def _transformAuthor(author: dict) -> Optional[Dict]:
    if (not author['last_name']) and (not author['first_name']):
        return None
    author['full_name'] = re.sub(r'\s+', ' ', f"{author['first_name']} {author['last_name']}")
    author['initials'] = " ".join([pt[0] for pt in author['first_name'].split() if pt])
    name_parts = author['first_name'].split() + author['last_name'].split()
    author['full_name_initialized'] = ' '.join([part[0] for part in name_parts[:-1]] + [name_parts[-1]])
    return author


def _constructAuthors(meta: DocMeta) -> List[Dict]:
    _authors = []
    for author in meta.authors_parsed:
        _author = _transformAuthor(author)
        if _author:
            _authors.append(_author)
    return _authors


def _constructAuthorOwners(meta: DocMeta) -> List[Dict]:
    _authors = []
    for author in meta.author_owners:
        _author = _transformAuthor(author)
        if _author:
            _authors.append(_author)
    return _authors


def _getFirstSubDate(meta: DocMeta) -> Optional[str]:
    if not meta.submitted_date_all:
        return None
    return meta.submitted_date_all[0]


def _getLastSubDate(meta: DocMeta) -> Optional[str]:
    if not meta.submitted_date_all:
        return None
    return meta.submitted_date_all[-1]


def _constructDOI(meta: DocMeta) -> List[str]:
    if meta.doi:
        return meta.doi.split()
    return []


TransformType = Union[str, Callable]
_transformations: List[Tuple[str, TransformType, bool]] = [
    ("id", _constructPaperVersion, True),
    ("abstract", "abstract_utf8", False),
    ("authors", _constructAuthors, True),
    ("authors_freeform", "authors_utf8", False),
    ("owners", _constructAuthorOwners, False),
    ("submitted_date", "submitted_date", True),
    ("submitted_date_all",
     lambda meta: meta.submitted_date_all if meta.is_current else None, True),
    ("submitted_date_first", _getFirstSubDate, True),
    ("submitted_date_latest", _getLastSubDate, True),
    ("modified_date", "modified_date", True),
    ("updated_date", "updated_date", True),
    ("announced_date_first", "announced_date_first", False),
    ("is_current", "is_current", True),
    ("is_withdrawn", "is_withdrawn", False),
    ("license", _constructLicense, True),
    ("paper_id", "paper_id", True),
    ("paper_id_v", _constructPaperVersion, True),
    ("primary_classification", "primary_classification", True),
    ("secondary_classification", "secondary_classification", True),
    ("title", "title_utf8", True),
    # ("title_tex", "title", True),
    ("source", "source", True),
    ("version", "version", True),
    ("submitter", "submitter", False),
    ("report_num", "report_num", False),
    ("proxy", "proxy", False),
    ("msc_class", _constructMSCClass, False),
    ("metadata_id", "metadata_id", False),
    ("journal_ref", "journal_ref_utf8", False),
    ("doi", _constructDOI, False),
    ("comments", "comments_utf8", False),
    ("acm_class", _constructACMClass, False),
    ("abs_categories", "abs_categories", False),
    ("formats", "formats", True),
    ("latest_version", "latest_version", True),
    ("latest", "latest", True)
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
    data = {}
    for key, source, is_required in _transformations:
        if isinstance(source, str):
            value = getattr(metadata, source, None)
        elif hasattr(source, '__call__'):
            value = source(metadata)
        if value is None and not is_required:
            continue
        data[key] = value
    if fulltext:
        data['fulltext'] = fulltext.content
    return Document(**data)     # type: ignore
    # See https://github.com/python/mypy/issues/3937
