"""Tests for :mod:`search.services.index`."""

from unittest import TestCase, mock
from unittest.mock import MagicMock
from datetime import datetime, timedelta

from search.services import index
from search.services.index import advanced
from search.services.index.util import wildcard_escape, Q_
from search.services.index import highlighting

from search.domain import (
    SortBy,
    SortOrder,
    FieldedSearchTerm,
    DateRange,
    Classification,
    AdvancedQuery,
    FieldedSearchList,
    ClassificationList,
    SimpleQuery,
    Field,
    Term,
    ClassicAPIQuery,
    Operator,
)


class TestClassicApiQuery(TestCase):
    """Test classic API queries."""

    def test_classic_query_creation(self):
        """Test classic API query creation."""
        self.assertRaises(ValueError, lambda: ClassicAPIQuery())
        # There is no assert not raises
        self.assertIsNotNone(ClassicAPIQuery(search_query=""))
        self.assertIsNotNone(ClassicAPIQuery(id_list=[]))

    def test_to_query_string(self):
        """Test classic API query string creation."""
        self.assertEqual(
            ClassicAPIQuery(id_list=[]).to_query_string(),
            "search_query=&id_list=&start=0&max_results=10",
        )
        self.assertEqual(
            ClassicAPIQuery(
                search_query="all:electron", id_list=[]
            ).to_query_string(),
            "search_query=all:electron&id_list=&start=0&max_results=10",
        )
        self.assertEqual(
            ClassicAPIQuery(
                search_query="all:electron",
                id_list=["1705.09169v3", "1705.09129v3"],
            ).to_query_string(),
            "search_query=all:electron&id_list=1705.09169v3,1705.09129v3"
            "&start=0&max_results=10",
        )
        self.assertEqual(
            ClassicAPIQuery(
                search_query="all:electron",
                id_list=["1705.09169v3", "1705.09129v3"],
                page_start=3,
            ).to_query_string(),
            "search_query=all:electron&id_list=1705.09169v3,1705.09129v3"
            "&start=3&max_results=10",
        )
        self.assertEqual(
            ClassicAPIQuery(
                search_query="all:electron",
                id_list=["1705.09169v3", "1705.09129v3"],
                page_start=3,
                size=50,
            ).to_query_string(),
            "search_query=all:electron&id_list=1705.09169v3,1705.09129v3"
            "&start=3&max_results=50",
        )
        self.assertEqual(
            ClassicAPIQuery(
                search_query="all:electron", page_start=3, size=50
            ).to_query_string(),
            "search_query=all:electron&id_list=&start=3&max_results=50",
        )
        self.assertEqual(
            ClassicAPIQuery(
                id_list=["1705.09169v3", "1705.09129v3"], page_start=3, size=50
            ).to_query_string(),
            "search_query=&id_list=1705.09169v3,1705.09129v3"
            "&start=3&max_results=50",
        )
        self.assertEqual(
            ClassicAPIQuery(
                search_query="all:electron", size=50
            ).to_query_string(),
            "search_query=all:electron&id_list=&start=0&max_results=50",
        )


class Hi:
    """Test of highlighting."""

    def __init__(self):
        self.abstract = "An " + highlighting.HIGHLIGHT_TAG_OPEN + "abstract"\
            + highlighting.HIGHLIGHT_TAG_CLOSE + " with math $/alpha * /alpha$ for you."
        self.autor = 'Smith B'
        self.title = 'some title'

def mock_rdata():
    """Provides mock result data."""            
    return {
        "authors": [{"full_name": "N. Ame"}],
        "owners": [{"full_name": "N. Ame"}],
        "submitter": {"full_name": "N. Ame"},
        "paper_id": "1234.56789",
        "title": "some title",
        "abstract": "An abstract with math $/alpha * /alpha$ for you.",
    }


class TestSearch(TestCase):
    """Tests for :func:`.index.search`."""

    @mock.patch("search.services.index.Search")
    @mock.patch("search.services.index.Elasticsearch")
    def test_advanced_query(self, mock_Elasticsearch, mock_Search):
        """:class:`.index.search` supports :class:`AdvancedQuery`."""
        mock_results = mock.MagicMock()        
        rdata = mock_rdata()
        mock_result = mock.MagicMock(_d_=rdata, **rdata)
        mock_result.meta.score = 1
        mock_results.__getitem__.return_value = {"total": 53}
        mock_results.__iter__.return_value = [mock_result]
        mock_result.meta.highlight = Hi()
        mock_Search.execute.return_value = mock_results

        # Support the chaining API for py-ES.        
        mock_Search.return_value = mock_Search
        mock_Search.filter.return_value = mock_Search
        mock_Search.highlight.return_value = mock_Search
        mock_Search.highlight_options.return_value = mock_Search
        mock_Search.query.return_value = mock_Search
        mock_Search.sort.return_value = mock_Search
        mock_Search.__getitem__.return_value = mock_Search

        query = AdvancedQuery(
            order="relevance",
            size=10,
            date_range=DateRange(
                start_date=datetime.now() - timedelta(days=5),
                end_date=datetime.now(),
            ),
            classification=ClassificationList(
                [
                    Classification(
                        group={"id": "physics"},
                        archive={"id": "physics"},
                        category={"id": "hep-th"},
                    )
                ]
            ),
            terms=FieldedSearchList(
                [
                    FieldedSearchTerm(
                        operator="AND", field="title", term="foo"
                    ),
                    FieldedSearchTerm(
                        operator="AND", field="author", term="joe"
                    ),
                    FieldedSearchTerm(
                        operator="OR", field="abstract", term="hmm"
                    ),
                    FieldedSearchTerm(
                        operator="NOT", field="comments", term="eh"
                    ),
                    FieldedSearchTerm(
                        operator="AND",
                        field="journal_ref",
                        term="jref (1999) 1:2-3",
                    ),
                    FieldedSearchTerm(
                        operator="AND", field="acm_class", term="abc123"
                    ),
                    FieldedSearchTerm(
                        operator="AND", field="msc_class", term="abc123"
                    ),
                    FieldedSearchTerm(
                        operator="OR", field="report_num", term="abc123"
                    ),
                    FieldedSearchTerm(
                        operator="OR", field="doi", term="10.01234/56789"
                    ),
                    FieldedSearchTerm(
                        operator="OR",
                        field="orcid",
                        term="0000-0000-0000-0000",
                    ),
                    FieldedSearchTerm(
                        operator="OR", field="author_id", term="Bloggs_J"
                    ),
                ]
            ),
        )

        document_set = index.SearchSession.search(query, highlight=True)
        self.assertEqual(document_set["metadata"]["start"], 0)
        self.assertEqual(int(document_set["metadata"]["total_results"]), 53)
        self.assertEqual(int(document_set["metadata"]["current_page"]), 1)
        self.assertEqual(document_set["metadata"]["total_pages"], 6)
        self.assertEqual(document_set["metadata"]["size"], 10)
        self.assertEqual(len(document_set["results"]), 1)

    @mock.patch("search.services.index.Search")
    @mock.patch("search.services.index.Elasticsearch")
    def test_simple_query(self, mock_Elasticsearch, mock_Search):
        """:class:`.index.search` supports :class:`SimpleQuery`."""
        mock_results = mock.MagicMock()
        mock_results.__getitem__.return_value = {"total": 53}
        rdata = mock_rdata()
        mock_result = mock.MagicMock(_d_=rdata, **rdata)
        mock_result.meta.score = 1
        mock_results.__iter__.return_value = [mock_result]
        mock_Search.execute.return_value = mock_results

        # Support the chaining API for py-ES.
        mock_Search.return_value = mock_Search
        mock_Search.filter.return_value = mock_Search
        mock_Search.highlight.return_value = mock_Search
        mock_Search.highlight_options.return_value = mock_Search
        mock_Search.query.return_value = mock_Search
        mock_Search.sort.return_value = mock_Search
        mock_Search.__getitem__.return_value = mock_Search

        query = SimpleQuery(
            order="relevance", size=10, search_field="title", value="foo title"
        )
        document_set = index.SearchSession.search(query, highlight=True)
        # self.assertIsInstance(document_set, DocumentSet)
        self.assertEqual(document_set["metadata"]["start"], 0)
        self.assertEqual(document_set["metadata"]["total_results"], 53)
        self.assertEqual(document_set["metadata"]["current_page"], 1)
        self.assertEqual(document_set["metadata"]["total_pages"], 6)
        self.assertEqual(document_set["metadata"]["size"], 10)
        self.assertEqual(len(document_set["results"]), 1)

    @mock.patch("search.services.index.Search")
    @mock.patch("search.services.index.Elasticsearch")
    def test_classic_query(self, mock_Elasticsearch, mock_Search):
        """:class:`.index.search` supports :class:`SimpleQuery`."""
        mock_results = mock.MagicMock()
        mock_results.__getitem__.return_value = {"total": 53}
        rdata = mock_rdata()
        mock_result = mock.MagicMock(_d_=rdata, **rdata)
        mock_result.meta.score = 1
        mock_results.__iter__.return_value = [mock_result]
        mock_Search.execute.return_value = mock_results

        # Support the chaining API for py-ES.
        mock_Search.return_value = mock_Search
        mock_Search.filter.return_value = mock_Search
        mock_Search.highlight.return_value = mock_Search
        mock_Search.highlight_options.return_value = mock_Search
        mock_Search.query.return_value = mock_Search
        mock_Search.sort.return_value = mock_Search
        mock_Search.__getitem__.return_value = mock_Search

        query = ClassicAPIQuery(
            phrase=Term(Field.Author, "copernicus"),
            order=SortOrder(by=SortBy.relevance),
            size=10,
        )

        document_set = index.SearchSession.search(query, highlight=True)
        # self.assertIsInstance(document_set, DocumentSet)
        self.assertEqual(document_set["metadata"]["start"], 0)
        self.assertEqual(document_set["metadata"]["total_results"], 53)
        self.assertEqual(document_set["metadata"]["current_page"], 1)
        self.assertEqual(document_set["metadata"]["total_pages"], 6)
        self.assertEqual(document_set["metadata"]["size"], 10)
        self.assertEqual(len(document_set["results"]), 1)

    @mock.patch("search.services.index.Search")
    @mock.patch("search.services.index.Elasticsearch")
    def test_classic_query_complex(self, mock_Elasticsearch, mock_Search):
        """:class:`.index.search` supports :class:`SimpleQuery`."""
        mock_results = mock.MagicMock()
        mock_results.__getitem__.return_value = {"total": 53}
        rdata = mock_rdata()
        mock_result = mock.MagicMock(_d_=rdata, **rdata)
        mock_result.meta.score = 1
        mock_results.__iter__.return_value = [mock_result]
        mock_Search.execute.return_value = mock_results

        # Support the chaining API for py-ES.
        mock_Search.return_value = mock_Search
        mock_Search.filter.return_value = mock_Search
        mock_Search.highlight.return_value = mock_Search
        mock_Search.highlight_options.return_value = mock_Search
        mock_Search.query.return_value = mock_Search
        mock_Search.sort.return_value = mock_Search
        mock_Search.__getitem__.return_value = mock_Search

        query = ClassicAPIQuery(
            phrase=(
                Operator.OR,
                Term(Field.Author, "copernicus"),
                (Operator.ANDNOT, Term(Field.Title, "dark matter")),
            ),
            order=SortOrder(by=SortBy.relevance),
            size=10,
        )

        document_set = index.SearchSession.search(query, highlight=True)
        # self.assertIsInstance(document_set, DocumentSet)
        self.assertEqual(document_set["metadata"]["start"], 0)
        self.assertEqual(document_set["metadata"]["total_results"], 53)
        self.assertEqual(document_set["metadata"]["current_page"], 1)
        self.assertEqual(document_set["metadata"]["total_pages"], 6)
        self.assertEqual(document_set["metadata"]["size"], 10)
        self.assertEqual(len(document_set["results"]), 1)

    @mock.patch("search.services.index.Search")
    @mock.patch("search.services.index.Elasticsearch")
    def test_classic_query_id_list(self, mock_Elasticsearch, mock_Search):
        """:class:`.index.search` supports :class:`SimpleQuery`."""
        mock_results = mock.MagicMock()
        mock_results.__getitem__.return_value = {"total": 53}
        rdata = mock_rdata()
        mock_result = mock.MagicMock(_d_=rdata, **rdata)
        mock_result.meta.score = 1
        mock_results.__iter__.return_value = [mock_result]
        mock_Search.execute.return_value = mock_results

        # Support the chaining API for py-ES.
        mock_Search.return_value = mock_Search
        mock_Search.filter.return_value = mock_Search
        mock_Search.highlight.return_value = mock_Search
        mock_Search.highlight_options.return_value = mock_Search
        mock_Search.query.return_value = mock_Search
        mock_Search.sort.return_value = mock_Search
        mock_Search.__getitem__.return_value = mock_Search

        query = ClassicAPIQuery(
            id_list=["1234.56789"],
            order=SortOrder(by=SortBy.relevance),
            size=10,
        )

        document_set = index.SearchSession.search(query, highlight=True)
        # self.assertIsInstance(document_set, DocumentSet)
        self.assertEqual(document_set["metadata"]["start"], 0)
        self.assertEqual(document_set["metadata"]["total_results"], 53)
        self.assertEqual(document_set["metadata"]["current_page"], 1)
        self.assertEqual(document_set["metadata"]["total_pages"], 6)
        self.assertEqual(document_set["metadata"]["size"], 10)
        self.assertEqual(len(document_set["results"]), 1)

    @mock.patch("search.services.index.Search")
    @mock.patch("search.services.index.Elasticsearch")
    def test_classic_query_phrases(self, mock_Elasticsearch, mock_Search):
        """:class:`.index.search` supports :class:`SimpleQuery`."""
        mock_results = mock.MagicMock()
        mock_results.__getitem__.return_value = {"total": 53}
        rdata = mock_rdata()
        mock_result = mock.MagicMock(_d_=rdata, **rdata)
        mock_result.meta.score = 1
        mock_results.__iter__.return_value = [mock_result]
        mock_Search.execute.return_value = mock_results

        # Support the chaining API for py-ES.
        mock_Search.return_value = mock_Search
        mock_Search.filter.return_value = mock_Search
        mock_Search.highlight.return_value = mock_Search
        mock_Search.highlight_options.return_value = mock_Search
        mock_Search.query.return_value = mock_Search
        mock_Search.sort.return_value = mock_Search
        mock_Search.__getitem__.return_value = mock_Search

        query = ClassicAPIQuery(
            phrase=(
                Operator.AND,
                Term(Field.Author, "copernicus"),
                Term(Field.Title, "philosophy"),
            ),
            order=SortOrder(by=SortBy.relevance),
            size=10,
        )

        document_set = index.SearchSession.search(query, highlight=True)
        # self.assertIsInstance(document_set, DocumentSet)
        self.assertEqual(document_set["metadata"]["start"], 0)
        self.assertEqual(document_set["metadata"]["total_results"], 53)
        self.assertEqual(document_set["metadata"]["current_page"], 1)
        self.assertEqual(document_set["metadata"]["total_pages"], 6)
        self.assertEqual(document_set["metadata"]["size"], 10)
        self.assertEqual(len(document_set["results"]), 1)


class TestWildcardSearch(TestCase):
    """A wildcard [*?] character is present in a querystring."""

    def test_match_any_wildcard_is_present(self):
        """A * wildcard is present in the query."""
        qs = "Foo t*"
        qs_escaped, wildcard = wildcard_escape(qs)

        self.assertTrue(wildcard, "Wildcard should be detected")
        self.assertEqual(qs, qs_escaped, "The querystring should be unchanged")
        self.assertIsInstance(
            Q_("match", "title", qs),
            type(index.Q("wildcard", title=qs)),
            "Wildcard Q object should be generated",
        )

    def test_match_any_wildcard_in_literal(self):
        """A * wildcard is present in a string literal."""
        qs = '"Foo t*"'
        qs_escaped, wildcard = wildcard_escape(qs)

        self.assertEqual(
            qs_escaped, r'"Foo t\*"', "Wildcard should be escaped"
        )
        self.assertFalse(wildcard, "Wildcard should not be detected")
        self.assertIsInstance(
            Q_("match", "title", qs),
            type(index.Q("match", title=r'"Foo t\*"')),
            "Wildcard Q object should not be generated",
        )

    def test_multiple_match_any_wildcard_in_literal(self):
        """Multiple * wildcards are present in a string literal."""
        qs = '"Fo*o t*"'
        qs_escaped, wildcard = wildcard_escape(qs)

        self.assertEqual(
            qs_escaped, r'"Fo\*o t\*"', "Both wildcards should be escaped"
        )
        self.assertFalse(wildcard, "Wildcard should not be detected")
        self.assertIsInstance(
            Q_("match", "title", qs),
            type(index.Q("match", title=r'"Fo\*o t\*"')),
            "Wildcard Q object should not be generated",
        )

    def test_mixed_wildcards_in_literal(self):
        """Both * and ? characters are present in a string literal."""
        qs = '"Fo? t*"'
        qs_escaped, wildcard = wildcard_escape(qs)

        self.assertEqual(
            qs_escaped, r'"Fo\? t\*"', "Both wildcards should be escaped"
        )
        self.assertFalse(wildcard, "Wildcard should not be detected")
        self.assertIsInstance(
            Q_("match", "title", qs),
            type(index.Q("match", title=r'"Fo\? t\*"')),
            "Wildcard Q object should not be generated",
        )

    def test_wildcards_both_inside_and_outside_literal(self):
        """Wildcard characters are present both inside and outside literal."""
        qs = '"Fo? t*" said the *'
        qs_escaped, wildcard = wildcard_escape(qs)

        self.assertEqual(
            qs_escaped,
            r'"Fo\? t\*" said the *',
            "Wildcards in literal should be escaped",
        )
        self.assertTrue(wildcard, "Wildcard should be detected")
        self.assertIsInstance(
            Q_("match", "title", qs),
            type(index.Q("wildcard", title=r'"Fo\? t\*" said the *')),
            "Wildcard Q object should be generated",
        )

    def test_wildcards_inside_outside_multiple_literals(self):
        """Wildcard chars are everywhere, and there are multiple literals."""
        qs = '"Fo?" s* "yes*" o?'
        qs_escaped, wildcard = wildcard_escape(qs)

        self.assertEqual(
            qs_escaped,
            r'"Fo\?" s* "yes\*" o?',
            "Wildcards in literal should be escaped",
        )
        self.assertTrue(wildcard, "Wildcard should be detected")

        self.assertIsInstance(
            Q_("match", "title", qs),
            type(index.Q("wildcard", title=r'"Fo\?" s* "yes\*" o?')),
            "Wildcard Q object should be generated",
        )

    def test_wildcard_at_opening_of_string(self):
        """A wildcard character is the first character in the querystring."""
        with self.assertRaises(index.QueryError):
            wildcard_escape("*nope")

        with self.assertRaises(index.QueryError):
            Q_("match", "title", "*nope")


class TestPrepare(TestCase):
    """Tests for :mod:`.index.prepare`."""

    def test_group_terms(self):
        """:meth:`._group_terms` groups terms using logical precedence."""
        query = AdvancedQuery(
            terms=FieldedSearchList(
                [
                    FieldedSearchTerm(
                        operator=None, field="title", term="muon"
                    ),
                    FieldedSearchTerm(
                        operator="OR", field="title", term="gluon"
                    ),
                    FieldedSearchTerm(
                        operator="NOT", field="title", term="foo"
                    ),
                    FieldedSearchTerm(
                        operator="AND", field="title", term="boson"
                    ),
                ]
            )
        )
        expected = (
            FieldedSearchTerm(operator=None, field="title", term="muon"),
            "OR",
            (
                (
                    FieldedSearchTerm(
                        operator="OR", field="title", term="gluon"
                    ),
                    "NOT",
                    FieldedSearchTerm(
                        operator="NOT", field="title", term="foo"
                    ),
                ),
                "AND",
                FieldedSearchTerm(operator="AND", field="title", term="boson"),
            ),
        )
        try:
            terms = advanced._group_terms(query)
        except AssertionError:
            self.fail("Should result in a single group")
        self.assertEqual(expected, terms)

    def test_group_terms_all_and(self):
        """:meth:`._group_terms` groups terms using logical precedence."""
        query = AdvancedQuery(
            terms=FieldedSearchList(
                [
                    FieldedSearchTerm(
                        operator=None, field="title", term="muon"
                    ),
                    FieldedSearchTerm(
                        operator="AND", field="title", term="gluon"
                    ),
                    FieldedSearchTerm(
                        operator="AND", field="title", term="foo"
                    ),
                ]
            )
        )
        expected = (
            (
                FieldedSearchTerm(operator=None, field="title", term="muon"),
                "AND",
                FieldedSearchTerm(operator="AND", field="title", term="gluon"),
            ),
            "AND",
            FieldedSearchTerm(operator="AND", field="title", term="foo"),
        )
        try:
            terms = advanced._group_terms(query)
        except AssertionError:
            self.fail("Should result in a single group")
        self.assertEqual(expected, terms)
