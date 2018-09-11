"""Serializers for API responses."""

from typing import Union
from lxml import etree
from flask import jsonify, url_for

from arxiv import status
from search.domain import DocumentSet, Document, Classification, Person


class BaseSerializer(object):
    """Base class for API serializers."""

    # def __init__(cls, document_set: DocumentSet) -> None:
    #     """Initialize with a :class:`DocumentSet`."""
        # cls._document_set = document_set


# class AtomXMLSerializer(BaseSerializer):
#     """."""
#
#     ATOM = "http://www.w3.org/2005/Atom"
#     OPENSEARCH = "http://a9.com/-/spec/opensearch/1.1/"
#     ARXIV = "http://arxiv.org/schemas/atom"
#     NSMAP = {
#         None: ATOM,
#         "opensearch": OPENSEARCH,
#         "arxiv": ARXIV
#     }
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
    def _transform_classification(cls, clsn: Classification) -> dict:
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
    def _transform_latest(cls, document: Document) -> dict:
        return {
            "paper_id": document.latest,
            "href": url_for("api.paper", paper_id=document.paper_id,
                            version=document.latest_version,
                            _external=True),
            "version": document.latest_version
        }

    @classmethod
    def _transform_license(cls, license: dict) -> dict:
        return {
            'label': license['label'],
            'href': license['uri']
        }

    @classmethod
    def transform_document(cls, doc: Document) -> dict:
        """Select a subset of :class:`Document` properties for public API."""
        return {
            'abs_categories': doc.abs_categories,
            'abstract': doc.abstract,
            'acm_class': doc.acm_class,
            'owners': [
                cls._transform_person(owner) for owner in doc.owners
            ],
            'authors': [
                cls._transform_person(author) for author in doc.authors
            ],
            'comments': doc.comments,
            'submitted_date': doc.submitted_date,
            'submitted_date_first': doc.submitted_date_first,
            'announced_date_first': doc.announced_date_first.strftime('%Y-%m'),
            'paper_id': doc.paper_id_v,
            'doi': doc.doi,
            'formats': [
                cls._transform_format(fmt, doc.paper_id, doc.version)
                for fmt in doc.formats
            ],
            'is_current': doc.is_current,
            'is_withdrawn': doc.is_withdrawn,
            'journal_ref': doc.journal_ref,
            'license': cls._transform_license(doc.license),
            'msc_class': doc.msc_class,
            'primary_classification': cls._transform_classification(
                doc.primary_classification
            ),
            'secondary_classification': [
                cls._transform_classification(clsn)
                for clsn in doc.secondary_classification
            ],
            'report_num': doc.report_num,
            'source': doc.source,  # TODO: link?
            'submitter': cls._transform_person(doc.submitter),
            'title': doc.title,
            'version': doc.version,
            'latest': cls._transform_latest(doc),
        }

    @classmethod
    def serialize(cls, document_set: DocumentSet) -> str:
        """Generate JSON for a :class:`DocumentSet`."""
        return jsonify({
            'results': [
                cls.transform_document(doc)
                for doc in document_set.results
            ],
            'metadata': {
                'start': document_set.metadata.get('start'),
                'end': document_set.metadata.get('end'),
                'size': document_set.metadata.get('size'),
                'total': document_set.metadata.get('total'),
            },
        })

    @classmethod
    def serialize_document(cls, document: Document) -> str:
        """Generate JSON for a single :class:`Document`."""
        return jsonify(cls.transform_document(document))


def as_json(document_or_document_set: Union[DocumentSet, Document]) -> str:
    """Serialize a :class:`DocumentSet` as JSON."""
    if type(document_or_document_set) is DocumentSet:
        return JSONSerializer.serialize(document_or_document_set)
    return JSONSerializer.serialize_document(document_or_document_set)
