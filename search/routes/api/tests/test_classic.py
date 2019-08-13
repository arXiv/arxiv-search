"""Tests for API routes."""

import os
import json
from datetime import datetime
from unittest import TestCase, mock

import jsonschema
import pytz

from arxiv.users import helpers, auth
from arxiv.users.domain import Scope
from arxiv import status

from search import factory
from search import domain


class TestClassicAPISearchRequests(TestCase):
    """Requests against the classic search API."""

    def setUp(self):
        """Instantiate and configure an API app."""
        jwt_secret = 'foosecret'
        os.environ['JWT_SECRET'] = jwt_secret
        self.app = factory.create_classic_api_web_app()
        self.app.config['JWT_SECRET'] = jwt_secret
        self.client = self.app.test_client()

    def test_request_without_token(self):
        """No auth token is provided on the request."""
        response = self.client.get('/classic/query?search_query=au:copernicus')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_with_token_lacking_scope(self):
        """Client auth token lacks required public read scope."""
        token = helpers.generate_token('1234', 'foo@bar.com', 'foouser',
                                       scope=[Scope('something', 'read')])
        response = self.client.get(
            '/classic/query?search_query=au:copernicus',
            headers={'Authorization': token})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch(f'{factory.__name__}.api.classic.api')
    def test_with_valid_token(self, mock_controller):
        """Client auth token has required public read scope."""
        document = dict(
            submitted_date=datetime.now(pytz.utc),
            submitted_date_first=datetime.now(pytz.utc),
            announced_date_first=datetime.now(pytz.utc),
            id='1234.5678',
            abstract='very abstract',
            authors=[
                dict(full_name='F. Bar', orcid='1234-5678-9012-3456')
            ],
            submitter=dict(full_name='S. Ubmitter', author_id='su_1'),
            modified_date=datetime.now(pytz.utc),
            updated_date=datetime.now(pytz.utc),
            is_current=True,
            is_withdrawn=False,
            license={
                'uri': 'http://foo.license/1',
                'label': 'Notalicense 5.4'
            },
            paper_id='1234.5678',
            paper_id_v='1234.5678v6',
            title='tiiiitle',
            source={
                'flags': 'A',
                'format': 'pdftotex',
                'size_bytes': 2
            },
            version=6,
            latest='1234.5678v6',
            latest_version=6,
            report_num='somenum1',
            msc_class=['c1'],
            acm_class=['z2'],
            journal_ref='somejournal (1991): 2-34',
            doi='10.123456/7890',
            comments='very science',
            abs_categories='astro-ph.CO foo.BR',
            formats=['pdf', 'other'],
            primary_classification=dict(
                group={'id': 'foo', 'name': 'Foo Group'},
                archive={'id': 'foo', 'name': 'Foo Archive'},
                category={'id': 'foo.BR', 'name': 'Foo Category'},
            ),
            secondary_classification=[
                dict(
                    group={'id': 'foo', 'name': 'Foo Group'},
                    archive={'id': 'foo', 'name': 'Foo Archive'},
                    category={'id': 'foo.BZ', 'name': 'Baz Category'},
                )
            ]
        )
        docs = dict(
            results=[document],
            metadata={'start': 0, 'end': 1, 'size': 50, 'total': 1}
        )
        r_data = {'results': docs, 'query': domain.ClassicAPIQuery(id_list=['1234.5678'])}
        mock_controller.classic_query.return_value = r_data, status.HTTP_200_OK, {}
        token = helpers.generate_token('1234', 'foo@bar.com', 'foouser',
                                       scope=[auth.scopes.READ_PUBLIC])
        response = self.client.get(
            '/classic/query?search_query=au:copernicus',
            headers={'Authorization': token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    @mock.patch(f'{factory.__name__}.api.classic.api')
    def test_paper_retrieval(self, mock_controller):
        """Test single-paper retrieval."""
        document = dict(
            submitted_date=datetime.now(pytz.utc),
            submitted_date_first=datetime.now(pytz.utc),
            announced_date_first=datetime.now(pytz.utc),
            id='1234.5678',
            abstract='very abstract',
            authors=[
                dict(full_name='F. Bar', orcid='1234-5678-9012-3456')
            ],
            submitter=dict(full_name='S. Ubmitter', author_id='su_1'),
            modified_date=datetime.now(pytz.utc),
            updated_date=datetime.now(pytz.utc),
            is_current=True,
            is_withdrawn=False,
            license={
                'uri': 'http://foo.license/1',
                'label': 'Notalicense 5.4'
            },
            paper_id='1234.5678',
            paper_id_v='1234.5678v6',
            title='tiiiitle',
            source={
                'flags': 'A',
                'format': 'pdftotex',
                'size_bytes': 2
            },
            version=6,
            latest='1234.5678v6',
            latest_version=6,
            report_num='somenum1',
            msc_class=['c1'],
            acm_class=['z2'],
            journal_ref='somejournal (1991): 2-34',
            doi='10.123456/7890',
            comments='very science',
            abs_categories='astro-ph.CO foo.BR',
            formats=['pdf', 'other'],
            primary_classification=dict(
                group={'id': 'foo', 'name': 'Foo Group'},
                archive={'id': 'foo', 'name': 'Foo Archive'},
                category={'id': 'foo.BR', 'name': 'Foo Category'},
            ),
            secondary_classification=[
                dict(
                    group={'id': 'foo', 'name': 'Foo Group'},
                    archive={'id': 'foo', 'name': 'Foo Archive'},
                    category={'id': 'foo.BZ', 'name': 'Baz Category'},
                )
            ]
        )
        docs = dict(
            results=[document],
            metadata={'start': 0, 'end': 1, 'size': 50, 'total': 1}
        )
        r_data = {'results': docs, 'query': domain.APIQuery()}
        mock_controller.paper.return_value = r_data, status.HTTP_200_OK, {}
        token = helpers.generate_token('1234', 'foo@bar.com', 'foouser',
                                       scope=[auth.scopes.READ_PUBLIC])
        response = self.client.get('/classic/1234.56789v6', headers={'Authorization': token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
