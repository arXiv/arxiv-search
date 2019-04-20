"""Serializers for API responses."""

from typing import Union, Optional
from xml.etree import ElementTree as etree
from flask import jsonify, url_for

from arxiv import status
from search.domain import DocumentSet, Document, Classification, Person, \
    APIQuery


class BaseSerializer(object):
    """Base class for API serializers."""


class JSONSerializer(BaseSerializer):
    """Serializes a :class:`DocumentSet` as JSON."""

    @classmethod
    def _transform_classification(cls, clsn: Classification) -> Optional[dict]:
        category = clsn.get('category')
        if category is None:
            return None
        return {'group': clsn.get('group'),
                'archive': clsn.get('archive'),
                'category': category}

    @classmethod
    def _transform_format(cls, fmt: str, paper_id: str, version: int) -> dict:
        return {"format": fmt,
                "href": url_for(fmt, paper_id=paper_id, version=version)}

    @classmethod
    def _transform_latest(cls, document: Document) -> Optional[dict]:
        latest = document.get('latest')
        if latest is None:
            return None
        return {
            "paper_id": latest,
            "href": url_for("api.paper", paper_id=document['paper_id'],
                            version=document.get('latest_version'),
                            _external=True),
            "canonical": url_for("abs", paper_id=document['paper_id'],
                                 version=document.get('latest_version')),
            "version": document.get('latest_version')
        }

    @classmethod
    def _transform_license(cls, license: dict) -> Optional[dict]:
        uri = license.get('uri')
        if uri is None:
            return None
        return {'label': license.get('label', ''), 'href': uri}

    @classmethod
    def transform_document(cls, doc: Document,
                           query: Optional[APIQuery] = None) -> dict:
        """Select a subset of :class:`Document` properties for public API."""
        # Only return fields that have been explicitly requested.
        data = {}
        if query is not None:
            paper_id = doc['paper_id']
            version = doc.get('version')
            for field, value in doc.items():
                if query is not None and field not in query.include_fields:
                    continue
                if field == 'submitted_date_first' and value:
                    value = value.isoformat()
                elif field == 'announced_date_first' and value:
                    value = value.isoformat()
                elif field == 'formats' and value:
                    value = [cls._transform_format(fmt, paper_id, version)
                             for fmt in value]
                elif field == 'license' and value:
                    value = cls._transform_license(value)
                elif field == 'latest' and value:
                    value = cls._transform_latest(doc)

                data[field] = value

            data['href'] = url_for("api.paper", paper_id=paper_id,
                                   version=version, _external=True)
            data['canonical'] = url_for("abs", paper_id=paper_id,
                                        version=version)
        return data

    @classmethod
    def serialize(cls, document_set: DocumentSet,
                  query: Optional[APIQuery] = None) -> str:
        """Generate JSON for a :class:`DocumentSet`."""
        serialized: str = jsonify({
            'results': [cls.transform_document(doc, query=query)
                        for doc in document_set['results']],
            'metadata': {
                'start': document_set['metadata'].get('start', ''),
                'end': document_set['metadata'].get('end', ''),
                'size': document_set['metadata'].get('size', ''),
                'total': document_set['metadata'].get('total', ''),
                'query': document_set['metadata'].get('query', [])
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
    if 'paper_id' in document_or_set:
        return JSONSerializer.serialize_document(document_or_set, query=query)  # type: ignore
    return JSONSerializer.serialize(document_or_set, query=query)  # type: ignore



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
