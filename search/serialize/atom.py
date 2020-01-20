from typing import Union, Optional, Dict, Any
from datetime import datetime

from pytz import utc
from flask import url_for
from feedgen.feed import FeedGenerator

from search.domain import (
    Error, DocumentSet, Document, APIQuery, ClassicAPIQuery,
    document_set_from_documents
)
from search.serialize.atom_extensions import (
    ArXivExtension, ArXivEntryExtension, OpenSearchExtension, ARXIV_NS
)
from search.controllers.classic.classic_parser import phrase_to_query_string
from search.serialize.base import BaseSerializer


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

    @staticmethod
    def _get_feed(query: Optional[ClassicAPIQuery] = None) -> FeedGenerator:
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
                "href": url_for('classic.query', search_query=query_string,
                                start=query.page_start, max_results=query.size,
                                id_list=id_list),
                "type": 'application/atom+xml'})
        else:
            # TODO: Discuss better defaults
            fg.title("arXiv Search Results")
            fg.id("https://arxiv.org/")

        fg.updated(datetime.utcnow().replace(tzinfo=utc))
        return fg

    @classmethod
    def serialize(cls, document_set: DocumentSet,
                  query: Optional[ClassicAPIQuery] = None) -> str:
        """Generate Atom response for a :class:`DocumentSet`."""
        fg = cls._get_feed(query)

        # pylint struggles with the opensearch extensions, so we ignore
        # no-member here.
        # pylint: disable=no-member
        fg.opensearch.totalResults(
            document_set['metadata'].get('total_results')
        )
        fg.opensearch.itemsPerPage(document_set['metadata'].get('size'))
        fg.opensearch.startIndex(document_set['metadata'].get('start'))

        for doc in document_set['results']:
            cls.transform_document(fg, doc, query=query)

        return fg.atom_str(pretty=True)

    @classmethod
    def serialize_error(cls, error: Error, query: Optional[ClassicAPIQuery] = None) -> str:
        fg = cls._get_feed(query)

        # pylint struggles with the opensearch extensions, so we ignore
        # no-member here.
        # pylint: disable=no-member
        fg.opensearch.totalResults(1)
        fg.opensearch.itemsPerPage(1)
        fg.opensearch.startIndex(0)

        entry = fg.add_entry()
        entry.id(error.id)
        entry.title("Error")
        entry.summary(error.error)
        entry.updated(error.created)
        entry.link({'href': error.link, "rel": "alternate", "type": "text/html"})
        entry.arxiv.author({"name": error.author})

        return fg.atom_str(pretty=True)

    @classmethod
    def serialize_document(cls, document: Document,
                           query: Optional[ClassicAPIQuery] = None) -> str:
        """Generate Atom feed for a single :class:`Document`."""
        # Wrap the single document in a DocumentSet wrapper.
        document_set = document_set_from_documents([document])

        return cls.serialize(document_set, query=query)


def as_atom(document_or_set: Union[Error, DocumentSet, Document],
            query: Optional[APIQuery] = None) -> str:
    """Serialize a :class:`DocumentSet` as Atom."""
    if isinstance(document_or_set, Error):
        return AtomXMLSerializer.serialize_error(document_or_set, query=query)
    elif 'paper_id' in document_or_set:
        return AtomXMLSerializer.serialize_document(document_or_set, query=query)  # type: ignore
    return AtomXMLSerializer.serialize(document_or_set, query=query)  # type: ignore
