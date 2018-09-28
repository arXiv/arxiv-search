"""Serializers for API responses."""

from typing import Union, Optional
from lxml import etree
from flask import jsonify, url_for

from arxiv import status
from search.domain import DocumentSet, Document, Classification, Person, \
    APIQuery


class BaseSerializer(object):
    """Base class for API serializers."""


class JSONSerializer(BaseSerializer):
    """Serializes a :class:`DocumentSet` as JSON."""

    @classmethod
    def _transform_person(cls, person: Person) -> dict:
        return {
            'first_name': person.first_name,
            'last_name': person.last_name,
            'suffix': person.suffix,
            'affiliation': person.affiliation,
            'orcid': person.orcid,
            'author_id': person.author_id,
            'full_name': person.full_name,
        }

    @classmethod
    def _transform_classification(cls, clsn: Classification) -> Optional[dict]:
        if clsn.category is None:
            return None
        return {
            'group': clsn.group,
            'archive': clsn.archive,
            'category': clsn.category
        }

    @classmethod
    def _transform_format(cls, fmt: str, paper_id: str, version: int) -> dict:
        return {
            "format": fmt,
            "href": url_for(fmt, paper_id=paper_id, version=version)
        }

    @classmethod
    def _transform_latest(cls, document: Document) -> Optional[dict]:
        if not document.latest:
            return None
        return {
            "paper_id": document.latest,
            "href": url_for("api.paper", paper_id=document.paper_id,
                            version=document.latest_version,
                            _external=True),
            "canonical": url_for("abs", paper_id=document.paper_id,
                                 version=document.latest_version),
            "version": document.latest_version
        }

    @classmethod
    def _transform_license(cls, license: dict) -> dict:
        return {
            'label': license['label'],
            'href': license['uri']
        }

    @classmethod
    def transform_document(cls, doc: Document,
                           query: Optional[APIQuery] = None) -> dict:
        """Select a subset of :class:`Document` properties for public API."""
        fields = [
            ('abs_categories', doc.abs_categories),
            ('abstract', doc.abstract),
            ('acm_class', doc.acm_class),
            ('owners', [
                cls._transform_person(owner) for owner in doc.owners
                if owner is not None
            ]),
            ('authors', [
                cls._transform_person(author) for author in doc.authors
                if author is not None
            ]),
            ('comments', doc.comments),
            ('authors_freeform', doc.authors_freeform),
            ('submitted_date', doc.submitted_date),
            ('submitted_date_first', doc.submitted_date_first),
            ('announced_date_first', (
                doc.announced_date_first.strftime('%Y-%m')
                if doc.announced_date_first is not None
                else None
            )),
            ('paper_id', doc.paper_id),
            ('paper_id_v', doc.paper_id_v),
            ('doi', doc.doi),
            ('formats', [
                cls._transform_format(fmt, doc.paper_id, doc.version)
                for fmt in doc.formats
            ]),
            ('is_current', doc.is_current),
            ('is_withdrawn', doc.is_withdrawn),
            ('journal_ref', doc.journal_ref),
            ('license',
             cls._transform_license(doc.license) if doc.license else None),
            ('msc_class', doc.msc_class),
            ('primary_classification',
             cls._transform_classification(doc.primary_classification)
             if doc.primary_classification else None),
            ('secondary_classification', [
                cls._transform_classification(clsn)
                for clsn in doc.secondary_classification
            ]),
            ('report_num', doc.report_num),
            ('source', doc.source),  # TODO, link?
            ('submitter', (
                cls._transform_person(doc.submitter)
                if doc.submitter is not None else None
            )),
            ('title', doc.title),
            ('version', doc.version),
            ('latest', cls._transform_latest(doc)),
            ('href', url_for("api.paper", paper_id=doc.paper_id,
                             version=doc.version, _external=True)),
            ('canonical', url_for("abs", paper_id=doc.paper_id,
                                  version=doc.version))
        ]

        # Only return fields that have been explicitly requested.
        if query is not None:
            _data = {field: value for field, value in fields
                     if field in query.include_fields}
        else:
            _data = {field: value for field, value in fields}
        return _data

    @classmethod
    def serialize(cls, document_set: DocumentSet,
                  query: Optional[APIQuery] = None) -> str:
        """Generate JSON for a :class:`DocumentSet`."""
        serialized: str = jsonify({
            'results': [
                cls.transform_document(doc, query=query)
                for doc in document_set.results
            ],
            'metadata': {
                'start': document_set.metadata.get('start'),
                'end': document_set.metadata.get('end'),
                'size': document_set.metadata.get('size'),
                'total': document_set.metadata.get('total'),
            },
        })
        return serialized

    @classmethod
    def serialize_document(cls, document: Document,
                           query: Optional[APIQuery] = None) -> str:
        """Generate JSON for a single :class:`Document`."""
        serialized: str = jsonify(
            cls.transform_document(document, query=query)
        )
        return serialized


def as_json(document_or_set: Union[DocumentSet, Document],
            query: Optional[APIQuery] = None) -> str:
    """Serialize a :class:`DocumentSet` as JSON."""
    if type(document_or_set) is DocumentSet:
        return JSONSerializer.serialize(document_or_set, query=query)  # type: ignore
    return JSONSerializer.serialize_document(document_or_set, query=query)  # type: ignore


# TODO: implement me!
class AtomXMLSerializer(BaseSerializer):
    """Atom XML serializer for paper metadata."""

    ATOM = "http://www.w3.org/2005/Atom"
    OPENSEARCH = "http://a9.com/-/spec/opensearch/1.1/"
    ARXIV = "http://arxiv.org/schemas/atom"
    NSMAP = {
        None: ATOM,
        "opensearch": OPENSEARCH,
        "arxiv": ARXIV
    }
#     fields = {
#         'title': '{%s}title' % ATOM,
#         'id': '{%s}id' % ATOM,
#         'submitted_date': '{%s}published' % ATOM,
#         'modified_date': '{%s}updated' % ATOM,
#         'abstract': '{%s}summary' % ATOM,
#         ''
#     }
#
#     def __init__(cls, *args, **kwargs) -> None:
#         super(AtomXMLSerializer, cls).__init__(*args, **kwargs)
#         cls._root = etree.Element('feed', nsmap=cls.NSMAP)
#
#     def transform(cls):
#         for document in cls.iter_documents():
#
#
#
#     def __repr__(cls) -> str:
#         return etree.tostring(cls._root, pretty_print=True)
