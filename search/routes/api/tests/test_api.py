"""Tests for API routes."""

import os
import json
from datetime import datetime
from unittest import TestCase, mock

import jsonschema

from arxiv.users import helpers, auth
from arxiv.users.domain import Scope
from arxiv import status

from search import factory
from search import domain


class TestAPISearchRequests(TestCase):
    """Requests against the main search API."""

    SCHEMA_PATH = os.path.abspath('schema/resources/DocumentSet.json')

    def setUp(self):
        """Instantiate and configure an API app."""
        jwt_secret = 'foosecret'
        os.environ['JWT_SECRET'] = jwt_secret
        self.app = factory.create_api_web_app()
        self.app.config['JWT_SECRET'] = jwt_secret
        self.client = self.app.test_client()

        with open(self.SCHEMA_PATH) as f:
            self.schema = json.load(f)

    def test_request_without_token(self):
        """No auth token is provided on the request."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_with_token_lacking_scope(self):
        """Client auth token lacks required public read scope."""
        token = helpers.generate_token('1234', 'foo@bar.com', 'foouser',
                                       scope=[Scope('something', 'read')])
        response = self.client.get('/', headers={'Authorization': token})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch(f'{factory.__name__}.api.api')
    def test_with_valid_token(self, mock_api_controller):
        """Client auth token has required public read scope."""
        document = domain.Document(
            submitted_date=datetime.now(),
            submitted_date_first=datetime.now(),
            announced_date_first=datetime.now(),
            id='1234.5678',
            abstract='very abstract',
            authors=[
                domain.Person(full_name='F. Bar', orcid='1234-5678-9012-3456')
            ],
            submitter=domain.Person(full_name='S. Ubmitter', author_id='su_1'),
            modified_date=datetime.now(),
            updated_date=datetime.now(),
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
            primary_classification=domain.Classification(
                group={'id': 'foo', 'name': 'Foo Group'},
                archive={'id': 'foo', 'name': 'Foo Archive'},
                category={'id': 'foo.BR', 'name': 'Foo Category'},
            ),
            secondary_classification=[
                domain.Classification(
                    group={'id': 'foo', 'name': 'Foo Group'},
                    archive={'id': 'foo', 'name': 'Foo Archive'},
                    category={'id': 'foo.BZ', 'name': 'Baz Category'},
                )
            ]
        )
        docs = domain.DocumentSet(
            results=[document],
            metadata={'start': 0, 'end': 1, 'size': 50, 'total': 1}
        )
        mock_api_controller.search.return_value = docs, status.HTTP_200_OK, {}
        token = helpers.generate_token('1234', 'foo@bar.com', 'foouser',
                                       scope=[auth.scopes.READ_PUBLIC])
        response = self.client.get('/', headers={'Authorization': token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = json.loads(response.data)
        res = jsonschema.RefResolver(
            'file://%s/' % os.path.abspath(os.path.dirname(self.SCHEMA_PATH)),
            None
        )
        self.assertIsNone(jsonschema.validate(data, self.schema, resolver=res),
                          'Response content is valid per schema')
