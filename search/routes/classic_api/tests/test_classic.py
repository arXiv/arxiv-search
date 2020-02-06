"""Tests for API routes."""

import os
from http import HTTPStatus
from xml.etree import ElementTree
from unittest import TestCase, mock

from arxiv.users import helpers, auth
from arxiv.users.domain import Scope
from search import factory
from search import domain
from search.tests import mocks


class TestClassicAPISearchRequests(TestCase):
    """Requests against the classic search API."""

    def setUp(self):
        """Instantiate and configure an API app."""
        jwt_secret = "foosecret"
        os.environ["JWT_SECRET"] = jwt_secret
        self.app = factory.create_classic_api_web_app()
        self.app.config["JWT_SECRET"] = jwt_secret
        self.client = self.app.test_client()
        self.auth_header = {
            "Authorization": helpers.generate_token(
                "1234",
                "foo@bar.com",
                "foouser",
                scope=[auth.scopes.READ_PUBLIC],
            )
        }

    def test_request_without_token(self):
        """No auth token is provided on the request."""
        response = self.client.get(
            "/classic_api/query?search_query=au:copernicus"
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_with_token_lacking_scope(self):
        """Client auth token lacks required public read scope."""
        token = helpers.generate_token(
            "1234",
            "foo@bar.com",
            "foouser",
            scope=[Scope("something", "read")],
        )
        response = self.client.get(
            "/classic_api/query?search_query=au:copernicus",
            headers={"Authorization": token},
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    @mock.patch(f"{factory.__name__}.classic_api.classic_api")
    def test_with_valid_token(self, mock_controller):
        """Client auth token has required public read scope."""
        document = mocks.document()
        docs = {
            "results": [document],
            "metadata": {"start": 0, "end": 1, "size": 50, "total": 1},
        }
        r_data = {
            "results": docs,
            "query": domain.ClassicAPIQuery(id_list=["1234.5678"]),
        }
        mock_controller.query.return_value = r_data, HTTPStatus.OK, {}
        response = self.client.get(
            "/classic_api/query?search_query=au:copernicus",
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @mock.patch(f"{factory.__name__}.classic_api.classic_api")
    def test_paper_retrieval(self, mock_controller):
        """Test single-paper retrieval."""
        document = mocks.document()
        docs = {
            "results": [document],
            "metadata": {"start": 0, "end": 1, "size": 50, "total": 1},
        }
        r_data = {"results": docs, "query": domain.APIQuery()}
        mock_controller.paper.return_value = r_data, HTTPStatus.OK, {}
        response = self.client.get(
            "/classic_api/1234.56789v6", headers=self.auth_header
        )
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
        """Return the text content of the node"""
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
            "/classic_api/query?search_query=au:copernicus&start=non_number",
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            "start must be an integer",
            "http://arxiv.org/api/errors#start_must_be_an_integer",
        )

    def test_start_negative(self):
        response = self.client.get(
            "/classic_api/query?search_query=au:copernicus&start=-1",
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            "start must be non-negative",
            "http://arxiv.org/api/errors#start_must_be_non-negative",
        )

    def test_max_results_not_a_number(self):
        response = self.client.get(
            "/classic_api/query?search_query=au:copernicus&"
            "max_results=non_number",
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            "max_results must be an integer",
            "http://arxiv.org/api/errors#max_results_must_be_an_integer",
        )

    def test_max_results_negative(self):
        response = self.client.get(
            "/classic_api/query?search_query=au:copernicus&max_results=-1",
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            "max_results must be non-negative",
            "http://arxiv.org/api/errors#max_results_must_be_non-negative",
        )

    def test_invalid_arxiv_id(self):
        response = self.client.get(
            "/classic_api/query?id_list=cond—mat/0709123",
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.check_validation_error(
            response,
            "incorrect id format for cond—mat/0709123",
            "http://arxiv.org/api/errors#"
            "incorrect_id_format_for_cond—mat/0709123",
        )
