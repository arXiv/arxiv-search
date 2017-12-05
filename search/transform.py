"""Responsible for transforming metadata/fulltext into a search document."""


def _constructPaperVersion(meta: dict) -> str:
    """Generate a version-qualified paper ID."""
    if 'v' in meta['paper_id']:
        return meta['paper_id']
    return '%sv%i' % (meta['paper_id'], meta.get('version', 1))


def _constructMSCClass(meta: dict) -> dict:
    """Extract ``msc_class`` field as an array."""
    raw = meta.get('msc_class')
    if not raw:
        return
    return [obj.strip() for obj in raw.split(',')]


def _constructACMClass(meta: dict) -> dict:
    """Extract ``acm_class`` field as an array."""
    raw = meta.get('acm_class')
    if not raw:
        return
    return [obj.strip() for obj in raw.split(';')]


_transformations = [
    ('abstract', 'abstract'),
    ('authors', "authors_parsed"),
    ('authors_freeform', "authors"),
    ("author_owners", "author_owners"),
    ("date_created", 'created'),
    ("date_modified", 'modtime'),
    ("date_updated", "updated"),
    ("is_current", "is_current"),
    ("is_withdrawn", "is_withdrawn"),
    ("license", "license"),
    ('paper_id', 'paper_id'),
    ('paper_id_v', _constructPaperVersion),
    ("primary_category", "primary_category"),
    ("primary_archive", "primary_archive"),
    ("primary_group", "primary_group"),
    ("secondary_categories", "secondary_categories"),
    ("secondary_archives", "secondary_archives"),
    ("secondary_groups", "secondary_groups"),
    ("title", "title"),
    ("source", "source"),
    ("version", "version"),
    ("submitter", "submitter"),
    ("report_num", "report_num"),
    ("proxy", "proxy"),
    ("msc_class", _constructMSCClass),
    ("metadata_id", "metadata_id"),
    ("journal_ref", "journal_ref"),
    ("is_withdrawn", "is_withdrawn"),
    ("is_current", "is_current"),
    ("doi", "doi"),
    ("comments", "comments"),
    ("acm_class", _constructACMClass),
    ("abs_categories", "abs_categories")
]

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


def to_search_document(metadata: dict, fulltext: dict=None) -> dict:
    """
    Transform metadata (and fulltext) into a valid search document.

    Parameters
    ----------
    metadata : dict
        See :mod:`search.services.metadata`.
    fulltext : dict
        Includes extraction version and creation timestamp.
        See :mod:`search.services.fulltext`.

    Returns
    -------
    dict
        Conforms to schema ``schema/Document.json``.

    Raises
    ------
    ValueError
    """
    document = {}
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
