"""Tests for API routes."""

import os
from http import HTTPStatus
from xml.etree import ElementTree
from unittest import TestCase, mock, skip

from search import consts
from search import factory
from search import domain
from search.tests import mocks


class TestClassicAPISearchRequests(TestCase):
    """Requests against the classic search API."""

    def setUp(self):
        """Instantiate and configure an API app."""
        self.app = factory.create_classic_api_web_app()
        self.client = self.app.test_client()

    @staticmethod
    def mock_classic_controller(controller, method="query", **kwargs):
        docs: domain.DocumentSet = {
            "results": [mocks.document()],
            "metadata": {"start": 0, "end": 1, "size": 50, "total": 1},
        }
        r_data = domain.ClassicSearchResponseData(
            results=docs,
            query=domain.ClassicAPIQuery(
                **(kwargs or {"search_query": "all:electron"})
            ),
        )
        getattr(controller, method).return_value = r_data, HTTPStatus.OK, {}

    @mock.patch(f"{factory.__name__}.classic_api.classic_api")
    def test_with_valid_token(self, mock_controller):
        """Client auth token has required public read scope."""
        self.mock_classic_controller(mock_controller, id_list=["1234.5678"])
        response = self.client.get(
            "/api/query?search_query=au:copernicus"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @skip("Does not exist in perl version")
    @mock.patch(f"{factory.__name__}.classic_api.classic_api")
    def test_paper_retrieval(self, mock_controller):
        """Test single-paper retrieval."""
        self.mock_classic_controller(mock_controller, method="paper")
        response = self.client.get("/1234.56789v6")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    # Validation errors
    def _fix_path(self, path):
        return "/".join(
            [
                "{{http://www.w3.org/2005/Atom}}{}".format(p)
                for p in path.split("/")
            ]
        )

    def _node(self, et: ElementTree, path: str):
        """Return the node."""
        return et.find(self._fix_path(path))

    def _text(self, et: ElementTree, path: str):
        """Return the text content of the node."""
        return et.findtext(self._fix_path(path))

    def check_validation_error(self, response, error, link):
        et = ElementTree.fromstring(response.get_data(as_text=True))
        self.assertEqual(self._text(et, "entry/id"), link)
        self.assertEqual(self._text(et, "entry/title"), "Error")
        self.assertEqual(self._text(et, "entry/summary"), error)
        link_attrib = self._node(et, "entry/link").attrib
        self.assertEqual(link_attrib["href"], link)

    def test_start_not_a_number(self):
        response = self.client.get(
            "/api/query?search_query=au:copernicus&start=non_number"
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            "start must be an integer",
            "https://arxiv.org/api/errors#start_must_be_an_integer",
        )

    def test_start_negative(self):
        response = self.client.get(
            "/api/query?search_query=au:copernicus&start=-1"
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            "start must be non-negative",
            "https://arxiv.org/api/errors#start_must_be_non-negative",
        )

    def test_max_results_not_a_number(self):
        response = self.client.get(
            "/api/query?search_query=au:copernicus&" "max_results=non_number"
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            "max_results must be an integer",
            "https://arxiv.org/api/errors#max_results_must_be_an_integer",
        )

    def test_max_results_negative(self):
        response = self.client.get(
            "/api/query?search_query=au:copernicus&max_results=-1"
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            "max_results must be non-negative",
            "https://arxiv.org/api/errors#max_results_must_be_non-negative",
        )

    @mock.patch(f"{factory.__name__}.classic_api.classic_api")
    def test_sort_by_valid_values(self, mock_controller):
        self.mock_classic_controller(mock_controller)

        for value in domain.SortBy:
            response = self.client.get(
                f"/api/query?search_query=au:copernicus&" f"sortBy={value}"
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_sort_by_invalid_values(self):
        response = self.client.get(
            "/api/query?search_query=au:copernicus&sortBy=foo"
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            f"sortBy must be in: {', '.join(domain.SortBy)}",
            "https://arxiv.org/help/api/user-manual#sort",
        )

    @mock.patch(f"{factory.__name__}.classic_api.classic_api")
    def test_sort_direction_valid_values(self, mock_controller):
        self.mock_classic_controller(mock_controller)

        for value in domain.SortDirection:
            response = self.client.get(
                f"/api/query?search_query=au:copernicus&" f"sortOrder={value}"
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_sort_direction_invalid_values(self):
        response = self.client.get(
            "/api/query?search_query=au:copernicus&sortOrder=foo"
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            f"sortOrder must be in: {', '.join(domain.SortDirection)}",
            "https://arxiv.org/help/api/user-manual#sort",
        )

    def test_sort_order(self):
        # Default
        sort_order = domain.SortOrder(by=None)
        self.assertEqual(sort_order.to_es(), consts.DEFAULT_SORT_ORDER)

        # Relevance/Score
        sort_order = domain.SortOrder(by=domain.SortBy.relevance)
        self.assertEqual(sort_order.to_es(), [{"_score": {"order": "desc"}}])
        sort_order = domain.SortOrder(
            by=domain.SortBy.relevance,
            direction=domain.SortDirection.ascending,
        )
        self.assertEqual(sort_order.to_es(), [{"_score": {"order": "asc"}}])

        # Submitted date/Publication date
        sort_order = domain.SortOrder(by=domain.SortBy.submitted_date)
        self.assertEqual(
            sort_order.to_es(), [{"submitted_date_first": {"order": "desc"}}]
        )
        sort_order = domain.SortOrder(
            by=domain.SortBy.submitted_date,
            direction=domain.SortDirection.ascending,
        )
        self.assertEqual(
            sort_order.to_es(), [{"submitted_date_first": {"order": "asc"}}]
        )

        # Last update date/Update date
        sort_order = domain.SortOrder(by=domain.SortBy.last_updated_date)
        self.assertEqual(
            sort_order.to_es(), [{"submitted_date": {"order": "desc"}}]
        )
        sort_order = domain.SortOrder(
            by=domain.SortBy.last_updated_date,
            direction=domain.SortDirection.ascending,
        )
        self.assertEqual(
            sort_order.to_es(), [{"submitted_date": {"order": "asc"}}]
        )

    def test_invalid_arxiv_id(self):
        response = self.client.get(
            "/api/query?id_list=cond—mat/0709123"
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            "incorrect id format for cond—mat/0709123",
            "https://arxiv.org/api/errors#"
            "incorrect_id_format_for_cond—mat/0709123",
        )
