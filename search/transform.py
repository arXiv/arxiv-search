"""Responsible for transforming metadata/fulltext into a search document."""


def _constructPaperVersion(meta: dict) -> str:
    """Generate a version-qualified paper ID."""
    if 'v' in meta['paper_id']:
        return meta['paper_id']
    return '%sv%i' % (meta['paper_id'], meta.get('version', 1))


def _constructSource(meta: dict) -> dict:
    """Extract metadata about paper source."""
    source_flags = meta.get('source_flags', None)
    if not source_flags:    # Might be blank, or something else falsey.
        source_flags = None
    source_format = meta.get('source_format', None)
    if not source_format:    # Might be blank, or something else falsey.
        source_format = None
    return {
        'flags': source_flags,
        'format': source_format,
        'size_bytes': meta.get('source_size_bytes', 0)
    }


def _constructSubmitter(meta: dict) -> dict:
    """Extract metadata about the submitter of the paper."""
    return {
        'email': meta.get('submitter_email'),
        'name': meta.get('submitter_name'),
        'is_author': meta['proxy'] is None,    # TODO: is that correct?
        'author_id': '',   # TODO: ML will add this to docmeta.
        'orcid': ''   # TODO: ML will add this to docmeta.
    }


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
    ('authors', lambda meta:[{'last_name': 'foo'}]),   # TODO: ML to implement.
    ("date_created", 'created'),
    ("date_modified", 'modtime'),
    ("date_updated", "updated"),
    ("is_current", "is_current"),
    ("is_withdrawn", "is_withdrawn"),
    ("license", lambda meta: {"uri": meta['license']}),
    ('paper_id', 'paper_id'),
    ('paper_id_v', _constructPaperVersion),
    ("primary_category", lambda meta: {'id': 'foo', 'name': 'bar'}),
    ("primary_archive", lambda meta: {'id': 'foo', 'name': 'bar'}),
    ("primary_group", lambda meta: {'id': 'foo', 'name': 'bar'}),
    ("title", "title"),
    ("source", _constructSource),
    ("version", "version"),
    ("submitter", _constructSubmitter),
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
        print(key, source, value)
        if not value and key not in _required:
            continue
        document[key] = value
    if fulltext:
        document['fulltext'] = fulltext.get('content', '')
    return document
