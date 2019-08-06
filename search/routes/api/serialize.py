"""Serializers for API responses."""

from typing import Union, Optional, Dict, Any
from datetime import datetime
from xml.etree import ElementTree as etree
from flask import jsonify, url_for, Response

from feedgen.feed import FeedGenerator
from pytz import utc

from arxiv import status
from search.domain import DocumentSet, Document, Classification, Person, \
    APIQuery, ClassicAPIQuery, document_set_from_documents
from .atom_extensions import ArXivExtension, ArXivEntryExtension, \
    OpenSearchExtension, ARXIV_NS
from ...controllers.api.classic_parser import phrase_to_query_string

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
        data = {key: value for key, value in doc.items()
                if query is None or key in query.include_fields}
        paper_id = doc['paper_id']
        version = doc['version']
        if 'submitted_date_first' in data:
            data['submitted_date_first'] = \
                doc['submitted_date_first'].isoformat()
        if 'announced_date_first' in data:
            data['announced_date_first'] = \
                doc['announced_date_first'].isoformat()
        if 'formats' in data:
            data['formats'] = [cls._transform_format(fmt, paper_id, version)
                               for fmt in doc['formats']]
        if 'license' in data:
            data['license'] = cls._transform_license(doc['license'])
        if 'latest' in data:
            data['latest'] = cls._transform_latest(doc)

        data['href'] = url_for("api.paper", paper_id=paper_id,
                               version=version, _external=True)
        data['canonical'] = url_for("abs", paper_id=paper_id,
                                    version=version)
        return data

    @classmethod
    def serialize(cls, document_set: DocumentSet,
                  query: Optional[APIQuery] = None) -> Response:
        """Generate JSON for a :class:`DocumentSet`."""
        total_results = int(document_set['metadata'].get('total_results', 0))
        serialized: Response = jsonify({
            'results': [cls.transform_document(doc, query=query)
                        for doc in document_set['results']],
            'metadata': {
                'start': document_set['metadata'].get('start', ''),
                'end': document_set['metadata'].get('end', ''),
                'size': document_set['metadata'].get('size', ''),
                'total_results': total_results,
                'query': document_set['metadata'].get('query', [])
            },
        })
        return serialized

    @classmethod
    def serialize_document(cls, document: Document,
                           query: Optional[APIQuery] = None) -> Response:
        """Generate JSON for a single :class:`Document`."""
        serialized: Response = jsonify(
            cls.transform_document(document, query=query)
        )
        return serialized


def as_json(document_or_set: Union[DocumentSet, Document],
            query: Optional[APIQuery] = None) -> Response:
    """Serialize a :class:`DocumentSet` as JSON."""
    if 'paper_id' in document_or_set:
        return JSONSerializer.serialize_document(document_or_set, query=query)  # type: ignore
    return JSONSerializer.serialize(document_or_set, query=query)  # type: ignore



class AtomXMLSerializer(BaseSerializer):
    """Atom XML serializer for paper metadata."""

    @classmethod
    def transform_document(cls, fg: FeedGenerator, doc: Document,
                           query: Optional[ClassicAPIQuery] = None) -> None:
        """Select a subset of :class:`Document` properties for public API."""
        entry = fg.add_entry()
        entry.id(url_for("abs", paper_id=doc['paper_id'],
                         version=doc['version'], _external=True))
        entry.title(doc['title'])
        entry.summary(doc['abstract'])
        entry.published(doc['submitted_date'])
        entry.updated(doc['updated_date'])
        entry.link({'href': url_for("abs", paper_id=doc['paper_id'],
                                    version=doc['version'], _external=True),
                    "type": "text/html"})

        entry.link({'href': url_for("pdf", paper_id=doc['paper_id'],
                                    version=doc['version'], _external=True),
                    "type": "application/pdf", 'rel': 'related'})

        if doc.get('comments'):
            entry.arxiv.comment(doc['comments'])

        if doc.get('journal_ref'):
            entry.arxiv.journal_ref(doc['journal_ref'])

        if doc.get('doi'):
            entry.arxiv.doi(doc['doi'])

        if doc['primary_classification']['category'] is not None:
            entry.arxiv.primary_category(
                doc['primary_classification']['category']['id']
            )
            entry.category(
                term=doc['primary_classification']['category']['id'],
                scheme=ARXIV_NS
            )

        for category in doc['secondary_classification']:
            entry.category(
                term=category['category']['id'],
                scheme=ARXIV_NS
            )

        for author in doc['authors']:
            author_data: Dict[str, Any] = {
                "name": author['full_name']
            }
            if author.get('affiliation'):
                author_data['affiliation'] = author['affiliation']
            entry.arxiv.author(author_data)

    @classmethod
    def serialize(cls, document_set: DocumentSet,
                  query: Optional[ClassicAPIQuery] = None) -> str:
        """Generate Atom response for a :class:`DocumentSet`."""
        fg = FeedGenerator()
        fg.register_extension('opensearch', OpenSearchExtension)
        fg.register_extension("arxiv", ArXivExtension, ArXivEntryExtension,
                              rss=False)

        if query:
            if query.phrase is not None:
                query_string = phrase_to_query_string(query.phrase)
            else:
                query_string = ''

            if query.id_list:
                id_list = ','.join(query.id_list)
            else:
                id_list = ''

            fg.title(
                f'arXiv Query: search_query={query_string}'
                f'&start={query.page_start}&max_results={query.size}'
                f'&id_list={id_list}')
            fg.id(url_for('classic.query', search_query=query_string,
                          start=query.page_start, max_results=query.size,
                          id_list=id_list))
            fg.link({
                "href" : url_for('classic.query', search_query=query_string,
                                 start=query.page_start, max_results=query.size,
                                 id_list=id_list),
                "type": 'application/atom+xml'})
        else:
            # TODO: Discuss better defaults
            fg.title("arXiv Search Results")
            fg.id("https://arxiv.org/")

        fg.updated(datetime.utcnow().replace(tzinfo=utc))

        # pylint struggles with the opensearch extensions, so we ignore no-member here.
        # pylint: disable=no-member
        fg.opensearch.totalResults(
            document_set['metadata'].get('total_results')
        )
        fg.opensearch.itemsPerPage(document_set['metadata'].get('size'))
        fg.opensearch.startIndex(document_set['metadata'].get('start'))

        if query:
            for doc in document_set['results']:
                cls.transform_document(fg, doc, query=query)

        serialized: str = fg.atom_str(pretty=True)
        return serialized

    @classmethod
    def serialize_document(cls, document: Document,
                           query: Optional[ClassicAPIQuery] = None) -> str:
        """Generate Atom feed for a single :class:`Document`."""
        # Wrap the single document in a DocumentSet wrapper.
        document_set = document_set_from_documents([document])

        return cls.serialize(document_set, query=query)


def as_atom(document_or_set: Union[DocumentSet, Document],
            query: Optional[APIQuery] = None) -> str:
    """Serialize a :class:`DocumentSet` as Atom."""
    if 'paper_id' in document_or_set:
        return AtomXMLSerializer.serialize_document(document_or_set, query=query)  # type: ignore
    return AtomXMLSerializer.serialize(document_or_set, query=query)  # type: ignore
