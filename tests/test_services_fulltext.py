# """Tests for :mod:`search.services.fulltext`."""
#
# import unittest
# from unittest import mock
# from search.services import fulltext
#
#
# class TestRetrieveExistantContent(unittest.TestCase):
#     """Fulltext content is available for a paper."""
#
#     @mock.patch('search.services.fulltext.requests.get')
#     def test_calls_fulltext_endpoint(self, mock_get):
#         """:func:`.fulltext.retrieve` calls passed endpoint with GET."""
#         base = 'https://asdf.com/'
#         response = mock.MagicMock()
#         type(response).json = mock.MagicMock(return_value={
#             'content': 'The whole story',
#             'version': 0.1,
#             'created': '2017-08-30T08:24:58.525923'
#         })
#         response.status_code = 200
#         mock_get.return_value = response
#
#         fulltext_session = fulltext.current_session()
#         fulltext_session.endpoint = base
#
#         try:
#             fulltext_session.retrieve('1234.5678v3')
#         except Exception as e:
#             self.fail('Choked on valid response: %s' % e)
#         args, _ = mock_get.call_args
#         self.assertTrue(args[0].startswith(base))
#
#     @mock.patch('search.services.fulltext.requests.get')
#     def test_returns_dict(self, mock_get):
#         """:func:`.fulltext.retrieve` returns a ``dict``."""
#         response = mock.MagicMock()
#         type(response).json = mock.MagicMock(return_value={
#             'content': 'The whole story',
#             'version': 0.1,
#             'created': '2017-08-30T08:24:58.525923'
#         })
#         response.status_code = 200
#         mock_get.return_value = response
#         try:
#             data = fulltext.retrieve('1234.5678v3')
#         except Exception as e:
#             self.fail('Choked on valid response: %s' % e)
#         self.assertIsInstance(data, dict)
#
#
# class TestRetrieveNonexistantRecord(unittest.TestCase):
#     """Fulltext content is not available for a paper."""
#
#     @mock.patch('search.services.fulltext.requests.get')
#     def test_raise_ioerror_on_404(self, mock_get):
#         """:func:`.fulltext.retrieve` raises IOError when text unvailable."""
#         response = mock.MagicMock()
#         type(response).json = mock.MagicMock(return_value=None)
#         response.status_code = 404
#         mock_get.return_value = response
#         with self.assertRaises(IOError):
#             fulltext.retrieve('1234.5678v3')
#
#     @mock.patch('search.services.fulltext.requests.get')
#     def test_raise_ioerror_on_503(self, mock_get):
#         """:func:`.fulltext.retrieve` raises IOError when text unvailable."""
#         response = mock.MagicMock()
#         type(response).json = mock.MagicMock(return_value=None)
#         response.status_code = 503
#         mock_get.return_value = response
#         with self.assertRaises(IOError):
#             fulltext.retrieve('1234.5678v3')
#
#     @mock.patch('search.services.fulltext.requests.get')
#     def test_raise_ioerror_on_sslerror(self, mock_get):
#         """:func:`.fulltext.retrieve` raises IOError when SSL fails."""
#         from requests.exceptions import SSLError
#         mock_get.side_effect = SSLError
#         with self.assertRaises(IOError):
#             try:
#                 fulltext.retrieve('1234.5678v3')
#             except Exception as e:
#                 if type(e) is SSLError:
#                     self.fail('Should not return dependency exception')
#                 raise
#
#
# class TestRetrieveMalformedRecord(unittest.TestCase):
#     """Fulltext endpoint returns non-JSON response."""
#
#     @mock.patch('search.services.fulltext.requests.get')
#     def test_response_is_not_json(self, mock_get):
#         """:func:`.fulltext.retrieve` raises IOError when not valid JSON."""
#         from json.decoder import JSONDecodeError
#         response = mock.MagicMock()
#
#         # Ideally we would pass the exception itself as a side_effect, but it
#         #  doesn't have the expected signature.
#         def raise_decodeerror(*args, **kwargs):
#             raise JSONDecodeError('Nope', 'Nope', 0)
#
#         type(response).json = mock.MagicMock(side_effect=raise_decodeerror)
#         response.status_code = 200
#         mock_get.return_value = response
#         with self.assertRaises(IOError):
#             fulltext.retrieve('1234.5678v3')
