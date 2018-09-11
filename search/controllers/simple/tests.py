"""Tests for simple search controller, :mod:`search.controllers.simple`."""

from unittest import TestCase, mock
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from werkzeug import MultiDict
from werkzeug.exceptions import InternalServerError, NotFound, BadRequest

from arxiv import status

from search.domain import Query, DateRange, SimpleQuery, DocumentSet

from search.controllers import simple
from search.controllers.simple.forms import SimpleSearchForm

from search.services.index import IndexConnectionError, QueryError, \
    DocumentNotFound


class TestRetrieveDocument(TestCase):
    """Tests for :func:`.simple.retrieve_document`."""

    @mock.patch('search.controllers.simple.index')
    def test_encounters_queryerror(self, mock_index):
        """There is a bug in the index or query."""
        # We need to explicit assign the exception to the mock, otherwise the
        #  exception raised in the side-effect will just be a mock object (not
        #  inheriting from BaseException).
        mock_index.QueryError = QueryError
        mock_index.IndexConnectionError = IndexConnectionError

        def _raiseQueryError(*args, **kwargs):
            raise QueryError('What now')

        mock_index.get_document.side_effect = _raiseQueryError

        with self.assertRaises(InternalServerError):
            try:
                response_data, code, headers = simple.retrieve_document(1)
            except QueryError as e:
                self.fail("QueryError should be handled (caught %s)" % e)

        self.assertEqual(mock_index.get_document.call_count, 1,
                         "A search should be attempted")

    @mock.patch('search.controllers.simple.index')
    def test_index_raises_connection_exception(self, mock_index):
        """Index service raises a IndexConnectionError."""
        # We need to explicit assign the exception to the mock, otherwise the
        #  exception raised in the side-effect will just be a mock object (not
        #  inheriting from BaseException).
        mock_index.IndexConnectionError = IndexConnectionError
        mock_index.QueryError = QueryError

        # def _raiseIndexConnectionError(*args, **kwargs):
        #     raise IndexConnectionError('What now')

        mock_index.get_document.side_effect = IndexConnectionError

        with self.assertRaises(InternalServerError):
            response_data, code, headers = simple.retrieve_document('124.5678')
        self.assertEqual(mock_index.get_document.call_count, 1,
                         "A search should be attempted")
        call_args, call_kwargs = mock_index.get_document.call_args
        self.assertIsInstance(call_args[0], str, "arXiv ID is passed")

        # self.assertEqual(code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @mock.patch('search.controllers.simple.index')
    def test_document_not_found(self, mock_index):
        """The document is not found."""
        # We need to explicit assign the exception to the mock, otherwise the
        #  exception raised in the side-effect will just be a mock object (not
        #  inheriting from BaseException).
        mock_index.QueryError = QueryError
        mock_index.IndexConnectionError = IndexConnectionError
        mock_index.DocumentNotFound = DocumentNotFound

        def _raiseDocumentNotFound(*args, **kwargs):
            raise DocumentNotFound('What now')

        mock_index.get_document.side_effect = _raiseDocumentNotFound

        with self.assertRaises(NotFound):
            try:
                response_data, code, headers = simple.retrieve_document(1)
            except DocumentNotFound as e:
                self.fail("DocumentNotFound should be handled (caught %s)" % e)

        self.assertEqual(mock_index.get_document.call_count, 1,
                         "A search should be attempted")


class TestSearchController(TestCase):
    """Tests for :func:`.simple.search`."""

    @mock.patch('search.controllers.simple.index')
    def test_arxiv_id(self, mock_index):
        """Query parameter contains an arXiv ID."""
        request_data = MultiDict({'query': '1702.00123'})
        response_data, code, headers = simple.search(request_data)
        self.assertEqual(code, status.HTTP_301_MOVED_PERMANENTLY,
                         "Response should be a 301 redirect.")
        self.assertIn('Location', headers, "Location header should be set")

        self.assertEqual(mock_index.search.call_count, 0,
                         "No search should be attempted")

    @mock.patch('search.controllers.simple.index')
    def test_no_form_data(self, mock_index):
        """No form data has been submitted."""
        request_data = MultiDict()
        response_data, code, headers = simple.search(request_data)
        self.assertEqual(code, status.HTTP_200_OK, "Response should be OK.")

        self.assertIn('form', response_data, "Response should include form.")

        self.assertEqual(mock_index.search.call_count, 0,
                         "No search should be attempted")

    @mock.patch('search.controllers.simple.index')
    def test_single_field_term(self, mock_index):
        """Form data are present."""
        mock_index.search.return_value = DocumentSet(metadata={}, results=[])
        request_data = MultiDict({
            'searchtype': 'title',
            'query': 'foo title'
        })
        response_data, code, headers = simple.search(request_data)
        self.assertEqual(mock_index.search.call_count, 1,
                         "A search should be attempted")
        call_args, call_kwargs = mock_index.search.call_args
        self.assertIsInstance(call_args[0], SimpleQuery,
                              "An SimpleQuery is passed to the search index")
        self.assertEqual(code, status.HTTP_200_OK, "Response should be OK.")

    @mock.patch('search.controllers.simple.index')
    def test_invalid_data(self, mock_index):
        """Form data are invalid."""
        request_data = MultiDict({
            'searchtype': 'title'
        })
        response_data, code, headers = simple.search(request_data)
        self.assertEqual(code, status.HTTP_200_OK, "Response should be OK.")

        self.assertIn('form', response_data, "Response should include form.")

        self.assertEqual(mock_index.search.call_count, 0,
                         "No search should be attempted")

    @mock.patch('search.controllers.simple.index')
    def test_index_raises_connection_exception(self, mock_index):
        """Index service raises a IndexConnectionError."""
        # We need to explicit assign the exception to the mock, otherwise the
        #  exception raised in the side-effect will just be a mock object (not
        #  inheriting from BaseException).
        mock_index.IndexConnectionError = IndexConnectionError

        def _raiseIndexConnectionError(*args, **kwargs):
            raise IndexConnectionError('What now')

        mock_index.search.side_effect = _raiseIndexConnectionError

        request_data = MultiDict({
            'searchtype': 'title',
            'query': 'foo title'
        })
        with self.assertRaises(InternalServerError):
            response_data, code, headers = simple.search(request_data)

        self.assertEqual(mock_index.search.call_count, 1,
                         "A search should be attempted")
        call_args, call_kwargs = mock_index.search.call_args
        self.assertIsInstance(call_args[0], SimpleQuery,
                              "An SimpleQuery is passed to the search index")

    @mock.patch('search.controllers.simple.index')
    def test_index_raises_query_error(self, mock_index):
        """Index service raises a QueryError."""
        # We need to explicit assign the exception to the mock, otherwise the
        #  exception raised in the side-effect will just be a mock object (not
        #  inheriting from BaseException).
        mock_index.QueryError = QueryError
        mock_index.IndexConnectionError = IndexConnectionError

        def _raiseQueryError(*args, **kwargs):
            raise QueryError('What now')

        mock_index.search.side_effect = _raiseQueryError

        request_data = MultiDict({
            'searchtype': 'title',
            'query': 'foo title'
        })
        with self.assertRaises(InternalServerError):
            try:
                response_data, code, headers = simple.search(request_data)
            except QueryError as e:
                self.fail("QueryError should be handled (caught %s)" % e)

        self.assertEqual(mock_index.search.call_count, 1,
                         "A search should be attempted")


class TestSimpleSearchForm(TestCase):
    """Tests for :class:`.SimpleSearchForm`."""

    def test_searchtype_only(self):
        """User has entered only a searchtype (field)."""
        data = MultiDict({
            'searchtype': 'title'
        })
        form = SimpleSearchForm(data)
        self.assertFalse(form.validate(), "Form should be invalid")

    def test_query_only(self):
        """User has entered only a query (value); this should never happen."""
        data = MultiDict({
            'query': 'someone monkeyed with the request'
        })
        form = SimpleSearchForm(data)
        self.assertFalse(form.validate(), "Form should be invalid")

    def test_query_and_searchtype(self):
        """User has entered a searchtype (field) and query (value)."""
        data = MultiDict({
            'searchtype': 'title',
            'query': 'foo title'
        })
        form = SimpleSearchForm(data)
        self.assertTrue(form.validate(), "Form should be valid")


class TestQueryFromForm(TestCase):
    """Tests for :func:`.simple._query_from_form`."""

    def test_multiple_simple(self):
        """Form data has three simple."""
        data = MultiDict({
            'searchtype': 'title',
            'query': 'foo title'
        })
        form = SimpleSearchForm(data)
        query = simple._query_from_form(form)
        self.assertIsInstance(query, SimpleQuery,
                              "Should return an instance of SimpleQuery")

    def test_form_data_has_order(self):
        """Form data includes sort order."""
        data = MultiDict({
            'searchtype': 'title',
            'query': 'foo title',
            'order': 'submitted_date'
        })
        form = SimpleSearchForm(data)
        query = simple._query_from_form(form)
        self.assertIsInstance(query, SimpleQuery,
                              "Should return an instance of SimpleQuery")
        self.assertEqual(query.order, 'submitted_date')

    def test_form_data_has_no_order(self):
        """Form data includes sort order parameter, but it is 'None'."""
        data = MultiDict({
            'searchtype': 'title',
            'query': 'foo title',
            'order': 'None'    #
        })
        form = SimpleSearchForm(data)
        query = simple._query_from_form(form)
        self.assertIsInstance(query, SimpleQuery,
                              "Should return an instance of SimpleQuery")
        self.assertIsNone(query.order, "Order should be None")

    def test_querystring_has_wildcard_at_start(self):
        """Querystring starts with a wildcard."""
        data = MultiDict({
            'searchtype': 'title',
            'query': '*foo title'
        })
        form = SimpleSearchForm(data)
        self.assertFalse(form.validate(), "Form should be invalid")

    def test_input_whitespace_is_stripped(self):
        """If query has padding whitespace, it should be removed."""
        data = MultiDict({
            'searchtype': 'title',
            'query': ' foo title '
        })
        form = SimpleSearchForm(data)
        self.assertTrue(form.validate(), "Form should be valid.")
        self.assertEqual(form.query.data, 'foo title')

    def test_querystring_has_unbalanced_quotes(self):
        """Querystring has an odd number of quote characters."""
        data = MultiDict({
            'searchtype': 'title',
            'query': '"rhubarb'
        })
        form = SimpleSearchForm(data)
        self.assertFalse(form.validate(), "Form should be invalid")

        data['query'] = '"rhubarb"'
        form = SimpleSearchForm(data)
        self.assertTrue(form.validate(), "Form should be valid")

        data['query'] = '"rhubarb" "pie'
        form = SimpleSearchForm(data)
        self.assertFalse(form.validate(), "Form should be invalid")

        data['query'] = '"rhubarb" "pie"'
        form = SimpleSearchForm(data)
        self.assertTrue(form.validate(), "Form should be valid")


class TestPaginationParametersAreFunky(TestCase):
    """
    The user may have monkeyed with the order or sort parameters.

    Since these are limited to specific values, there is no other reason for
    them to be invalid. Given that they are passed around among
    views (to persist users' selection), it's important to break the chain.
    To do this, we return a 400 Bad Request, with a clean link back to the
    search form.
    """

    @mock.patch('search.controllers.simple.url_for')
    def test_order_is_invalid(self, mock_url_for):
        """The order parameter on the request is invalid."""
        request_data = MultiDict({
            'searchtype': 'title',
            'query': 'foo title',
            'size': 50,     # Valid.
            'order': 'foo'  # Invalid
        })
        with self.assertRaises(BadRequest):
            simple.search(request_data)

    @mock.patch('search.controllers.simple.url_for')
    def test_size_is_invalid(self, mock_url_for):
        """The order parameter on the request is invalid."""
        request_data = MultiDict({
            'searchtype': 'title',
            'query': 'foo title',
            'size': 51,     # Invalid
            'order': ''  # Valid
        })
        with self.assertRaises(BadRequest):
            simple.search(request_data)


class TestClassicAuthorSyntaxIsIntercepted(TestCase):
    """
    The user may have entered an author query using `surname_f` syntax.

    This is an artefact of the classic search system, and not intended to be
    supported. Nevertheless, users have become accustomed to this syntax. We
    therefore rewrite the query using a comma, and show the user a warning
    about the syntax change.
    """

    @mock.patch('search.controllers.simple.index')
    def test_all_fields_search_contains_classic_syntax(self, mock_index):
        """User has entered a `surname_f` query in an all-fields search."""
        request_data = MultiDict({
            'searchtype': 'all',
            'query': 'franklin_r',
            'size': 50,
            'order': ''
        })
        mock_index.search.return_value = DocumentSet(metadata={}, results=[])

        data, code, headers = simple.search(request_data)
        self.assertEqual(data['query'].value, "franklin, r",
                         "The query should be rewritten.")
        self.assertTrue(data['has_classic_format'],
                        "A flag denoting the syntax interception should be set"
                        " in the response context, so that a message may be"
                        " rendered in the template.")

    @mock.patch('search.controllers.simple.index')
    def test_author_search_contains_classic_syntax(self, mock_index):
        """User has entered a `surname_f` query in an author search."""
        request_data = MultiDict({
            'searchtype': 'author',
            'query': 'franklin_r',
            'size': 50,
            'order': ''
        })
        mock_index.search.return_value = DocumentSet(metadata={}, results=[])

        data, code, headers = simple.search(request_data)
        self.assertEqual(data['query'].value, "franklin, r",
                         "The query should be rewritten.")
        self.assertTrue(data['has_classic_format'],
                        "A flag denoting the syntax interception should be set"
                        " in the response context, so that a message may be"
                        " rendered in the template.")

    @mock.patch('search.controllers.simple.index')
    def test_all_fields_search_multiple_classic_syntax(self, mock_index):
        """User has entered a classic query with multiple authors."""
        request_data = MultiDict({
            'searchtype': 'all',
            'query': 'j franklin_r hawking_s',
            'size': 50,
            'order': ''
        })
        mock_index.search.return_value = DocumentSet(metadata={}, results=[])

        data, code, headers = simple.search(request_data)
        self.assertEqual(data['query'].value, "j franklin, r; hawking, s",
                         "The query should be rewritten.")
        self.assertTrue(data['has_classic_format'],
                        "A flag denoting the syntax interception should be set"
                        " in the response context, so that a message may be"
                        " rendered in the template.")

    @mock.patch('search.controllers.simple.index')
    def test_title_search_contains_classic_syntax(self, mock_index):
        """User has entered a `surname_f` query in a title search."""
        request_data = MultiDict({
            'searchtype': 'title',
            'query': 'franklin_r',
            'size': 50,
            'order': ''
        })
        mock_index.search.return_value = DocumentSet(metadata={}, results=[])

        data, code, headers = simple.search(request_data)
        self.assertEqual(data['query'].value, "franklin_r",
                         "The query should not be rewritten.")
        self.assertFalse(data['has_classic_format'],
                         "Flag should not be set, as no rewrite has occurred.")
