"""Tests for :mod:`search.services.metadata`."""

import unittest
from unittest import mock
import json
import os
from itertools import cycle

from search.services import metadata
from search.factory import create_ui_web_app


class TestRetrieveExistantMetadata(unittest.TestCase):
    """Metadata is available for a paper."""

    @mock.patch('search.services.metadata.requests.get')
    def test_calls_metadata_endpoint(self, mock_get):
        """:func:`.metadata.retrieve` calls passed endpoint with GET."""
        base = 'https://asdf.com/'

        app = create_ui_web_app()
        app.config['METADATA_ENDPOINT'] = base

        response = mock.MagicMock()
        with open('tests/data/docmeta.json') as f:
            mock_content = json.load(f)

        type(response).json = mock.MagicMock(return_value=mock_content)
        response.status_code = 200
        mock_get.return_value = response

        with app.app_context():
            docmeta_session = metadata.get_session()

            try:
                docmeta_session.retrieve('1602.00123')
            except Exception as e:
                self.fail('Choked on valid response: %s' % e)
            try:
                args, _ = mock_get.call_args
            except Exception as e:
                self.fail('Did not call requests.get as expected: %s' % e)

        self.assertTrue(args[0].startswith(base))

    @mock.patch('search.services.metadata.requests.get')
    def test_calls_metadata_endpoint_roundrobin(self, mock_get):
        """:func:`.metadata.retrieve` calls passed endpoint with GET."""
        base = ['https://asdf.com/', 'https://asdf2.com/']
        app = create_ui_web_app()
        app.config['METADATA_ENDPOINT'] = ','.join(base)
        app.config['METADATA_VERIFY_CERT'] = 'False'

        response = mock.MagicMock()
        with open('tests/data/docmeta.json') as f:
            mock_content = json.load(f)

        type(response).json = mock.MagicMock(return_value=mock_content)
        response.status_code = 200
        mock_get.return_value = response

        with app.app_context():
            docmeta_session = metadata.get_session()

            try:
                docmeta_session.retrieve('1602.00123')
            except Exception as e:
                self.fail('Choked on valid response: %s' % e)
            try:
                args, _ = mock_get.call_args
            except Exception as e:
                self.fail('Did not call requests.get as expected: %s' % e)
            self.assertTrue(
                args[0].startswith(base[0]), "Expected call to %s" % base[0]
            )

            try:
                docmeta_session.retrieve('1602.00124')
            except Exception as e:
                self.fail('Choked on valid response: %s' % e)
            try:
                args, _ = mock_get.call_args
            except Exception as e:
                self.fail('Did not call requests.get as expected: %s' % e)
            self.assertTrue(
                args[0].startswith(base[1]), "Expected call to %s" % base[1]
            )


class TestRetrieveNonexistantRecord(unittest.TestCase):
    """Metadata is not available for a paper."""

    @mock.patch('search.services.metadata.requests.get')
    def test_raise_ioerror_on_404(self, mock_get):
        """:func:`.metadata.retrieve` raises IOError when unvailable."""
        response = mock.MagicMock()
        type(response).json = mock.MagicMock(return_value=None)
        response.status_code = 404
        mock_get.return_value = response
        with self.assertRaises(IOError):
            metadata.retrieve('1234.5678v3')

    @mock.patch('search.services.metadata.requests.get')
    def test_raise_ioerror_on_503(self, mock_get):
        """:func:`.metadata.retrieve` raises IOError when unvailable."""
        response = mock.MagicMock()
        type(response).json = mock.MagicMock(return_value=None)
        response.status_code = 503
        mock_get.return_value = response
        with self.assertRaises(IOError):
            metadata.retrieve('1234.5678v3')

    @mock.patch('search.services.metadata.requests.get')
    def test_raise_ioerror_on_sslerror(self, mock_get):
        """:func:`.metadata.retrieve` raises IOError when SSL fails."""
        from requests.exceptions import SSLError
        mock_get.side_effect = SSLError
        with self.assertRaises(IOError):
            try:
                metadata.retrieve('1234.5678v3')
            except Exception as e:
                if type(e) is SSLError:
                    self.fail('Should not return dependency exception')
                raise


class TestRetrieveMalformedRecord(unittest.TestCase):
    """Metadata endpoint returns non-JSON response."""

    @mock.patch('search.services.metadata.requests.get')
    def test_response_is_not_json(self, mock_get):
        """:func:`.metadata.retrieve` raises IOError when not valid JSON."""
        from json.decoder import JSONDecodeError
        response = mock.MagicMock()

        # Ideally we would pass the exception itself as a side_effect, but it
        #  doesn't have the expected signature.
        def raise_decodeerror(*args, **kwargs):
            raise JSONDecodeError('Nope', 'Nope', 0)

        type(response).json = mock.MagicMock(side_effect=raise_decodeerror)
        response.status_code = 200
        mock_get.return_value = response
        with self.assertRaises(IOError):
            metadata.retrieve('1234.5678v3')
