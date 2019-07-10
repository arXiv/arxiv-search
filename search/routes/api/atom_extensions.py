"""Feedgen extensions to implement serialization of the arXiv legacy API atom feed."""

from typing import Any, Dict
from feedgen.ext.base import BaseEntryExtension, BaseExtension
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from lxml import etree

ARXIV_NS = 'http://arxiv.org/schemas/atom'
OPENSEARCH_NS = 'http://a9.com/-/spec/opensearch/1.1/'

class OpenSearchExtension(BaseExtension):
    """Extension of the Feedgen base class to put OpenSearch metadata."""

    def __init__(self: BaseExtension) -> None:
        """Initialize extension parameters."""

        # __ syntax follows convention of :module:`feedgen.ext`
        self.__opensearch_totalResults = None
        self.__opensearch_startIndex = None
        self.__opensearch_itemsPerPage = None

    def extend_atom(self: BaseExtension, atom_feed: FeedGenerator) -> FeedGenerator:
        """
        Assign the Atom feed generator to the extension.

        Parameters
        ----------
        atom_feed : :class:`.FeedGenerator`
            The FeedGenerator to use for Atom results.

        Returns
        -------
        FeedGenerator
            The provided feed generator.

        """
        if self.__opensearch_itemsPerPage is not None:
            elt = etree.SubElement(atom_feed, f'{{{OPENSEARCH_NS}}}itemsPerPage')
            elt.text= self.__opensearch_itemsPerPage
        
        if self.__opensearch_totalResults is not None:
            elt = etree.SubElement(atom_feed, f'{{{OPENSEARCH_NS}}}totalResults')
            elt.text= self.__opensearch_totalResults

        if self.__opensearch_startIndex is not None:
            elt = etree.SubElement(atom_feed, f'{{{OPENSEARCH_NS}}}startIndex')
            elt.text = self.__opensearch_startIndex

        return atom_feed

    @staticmethod
    def extend_rss(rss_feed: FeedGenerator) -> FeedGenerator:
        """
        Assign the RSS feed generator to the extension.

        Parameters
        ----------
        rss_feed
            The FeedGenerator to use for RSS results.

        Returns
        -------
        FeedGenerator
            The provided feed generator.

        """
        return rss_feed

    @staticmethod
    def extend_ns() -> Dict[str, str]:
        """
        Assign the feed's namespace string.

        Returns
        -------
        str
            The definition string for the "arxiv" namespace.

        """
        return {'opensearch': OPENSEARCH_NS}

    def totalResults(self: BaseExtension, text: str):
        """ Set the totalResults parameter. """
        self.__opensearch_totalResults = str(text)

    def startIndex(self: BaseExtension, text: str):
        """ Set the startIndex parameter. """
        self.__opensearch_startIndex = str(text)
        
    def itemsPerPage(self: BaseExtension, text: str):
        """ Set the itemsPerPage parameter. """
        self.__opensearch_itemsPerPage = str(text)


class ArxivExtension(BaseExtension):
    """Extension of the Feedgen base class to allow us to define namespaces."""

    def __init__(self: BaseExtension) -> None:
        """Noop initialization."""
        pass

    @staticmethod
    def extend_atom(atom_feed: FeedGenerator) -> FeedGenerator:
        """
        Assign the Atom feed generator to the extension.

        Parameters
        ----------
        atom_feed
            The FeedGenerator to use for Atom results.

        Returns
        -------
        FeedGenerator
            The provided feed generator.

        """
        return atom_feed

    @staticmethod
    def extend_rss(rss_feed: FeedGenerator) -> FeedGenerator:
        """
        Assign the RSS feed generator to the extension.

        Parameters
        ----------
        rss_feed
            The FeedGenerator to use for RSS results.

        Returns
        -------
        FeedGenerator
            The provided feed generator.

        """
        return rss_feed

    @staticmethod
    def extend_ns() -> Dict[str, str]:
        """
        Assign the feed's namespace string.

        Returns
        -------
        str
            The definition string for the "arxiv" namespace.

        """
        return {'arxiv': ARXIV_NS}


class ArxivEntryExtension(BaseEntryExtension):
    """Extension of the Feedgen base class to allow us to add elements to the Atom output."""

    def __init__(self: BaseEntryExtension):
        """Initialize the member values to all be empty."""
        self.__arxiv_comment = None
        self.__arxiv_primary_category = None
        self.__arxiv_doi = None
        self.__arxiv_journal_ref = None
        self.__arxiv_authors = []

    def extend_atom(self: BaseEntryExtension, entry: FeedEntry) -> FeedEntry:
        """
        Add this extension's new elements to the Atom feed entry.

        Parameters
        ----------
        entry
            The FeedEntry to modify.

        Returns
        -------
        FeedEntry
            The modified entry.

        """
        if self.__arxiv_comment:
            comment_element = etree.SubElement(entry, f'{{{ARXIV_NS}}}comment')
            comment_element.text = self.__arxiv_comment

        if self.__arxiv_primary_category:
            primary_category_element = etree.SubElement(entry, f'{{{ARXIV_NS}}}primary_category')
            primary_category_element.attrib['term'] = self.__arxiv_primary_category

        if self.__arxiv_journal_ref:
            journal_ref_element = \
                etree.SubElement(entry, f'{{{ARXIV_NS}}}journal_ref')
            journal_ref_element.text = self.__arxiv_journal_ref

        if self.__arxiv_authors:
            for author in self.__arxiv_authors:
                author_element = etree.SubElement(entry, 'author')
                name_element = etree.SubElement(author_element, 'name')
                name_element.text = author['name']
                for affiliation in author.get('affiliation', []):
                    affiliation_element = \
                        etree.SubElement(author_element, 
                                         '{%s}affiliation' % ARXIV_NS)
                    affiliation_element.text = affiliation

        if self.__arxiv_doi:
            for doi in self.__arxiv_doi:
                doi_element = etree.SubElement(entry, f'{{{ARXIV_NS}}}doi')
                doi_element.text = doi

                doi_link_element = etree.SubElement(entry, 'link')
                doi_link_element.set('rel', 'related')
                doi_link_element.set('href', f'https://doi.org/{doi}')

        return entry

    @staticmethod
    def extend_rss(entry: FeedEntry) -> FeedEntry:
        """
        Add this extension's new elements to the RSS feed entry.

        Parameters
        ----------
        entry
            The FeedEntry to modify.

        Returns
        -------
        FeedEntry
            The modfied entry.

        """
        return entry

    def comment(self: BaseEntryExtension, text: str) -> None:
        """
        Assign the comment value to this entry.

        Parameters
        ----------
        text
            The new comment text.

        """
        self.__arxiv_comment = text

    def primary_category(self: BaseEntryExtension, text: str) -> None:
        """
        Assign the primary_category value to this entry.

        Parameters
        ----------
        text
            The new primary_category name.

        """
        self.__arxiv_primary_category = text

    def journal_ref(self: BaseEntryExtension, text: str) -> None:
        """
        Assign the journal_ref value to this entry.

        Parameters
        ----------
        text
            The new journal_ref value.

        """
        self.__arxiv_journal_ref = text

    def doi(self: BaseEntryExtension, list: Dict[str, str]) -> None:
        """
        Assign the doi value to this entry.

        Parameters
        ----------
        list
            The new list of DOI assignments.

        """
        self.__arxiv_doi = list
    
    def author(self: BaseEntryExtension, data: Dict[str, Any]) -> None:
        """
        Add an author to this entry.

        Parameters
        ----------
        data
            A dictionary consisting of the author name and affiliation data.
        """
        self.__arxiv_authors.append(data)
