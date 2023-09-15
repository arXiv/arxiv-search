"""Integration of search with :mod:`search.factory` and Kinesis.

Copied from :mod:`search.agent.tests.test_integration`
"""

from unittest import TestCase
import os

from search.factory import create_ui_web_app
from .integration import setup_for_integration_test, tear_down_integration
from search.controllers import simple

from werkzeug.datastructures import MultiDict

print('******************************')

class TestSearchWebAppIntegration(TestCase):
    """Test search requests against the web app with a live Elasticsearch."""

    __test__ = int(bool(os.environ.get("WITH_INTEGRATION", False)))
    
    @classmethod
    def setUpClass(cls):
        """Spin up ES and bulk index documents."""
        # cls.do_integration_setup = int(
        #     bool(os.environ.get("LAUNCH_INTEGRATION", False)))
        # if cls.do_integration_setup:
        #     cls.state = setup_for_integration_test()
        cls.app = create_ui_web_app()

    @classmethod
    def tearDownClass(cls):
        """Tear down Elasticsearch once all tests have run."""
        # if cls.do_integration_setup:
        #     tear_down_integration(cls.state)

    def test_search_controller(self):
        """Test running searches with ElasticSearch"""
        client = self.app.test_client()
        rv = client.get('/?query=Kowalczyk')
        self.assertEqual(rv.status_code, 200)

        # The HTML is too painful to use even with beautiful soup
        # so handle the results from the controller.
        with self.app.app_context():
            data, rs, _ = simple.search(
                MultiDict({'query': 'large', 'searchtype': 'all'}), None)
            self.assertTrue(
                len(data['results'][0]['highlight']['abstract']) > 0)

            # data, rs, _ = simple.search(
            #     MultiDict({'query': 'e subsets', 'searchtype': 'all'}), None)
            # self.assertTrue(
            #     len(data['results'][0]['highlight']['abstract']) > 0)

    def test_front_trunc(self):
        """Test that front truncation is okay."""
        with self.app.app_context():
            data, rs, _ = simple.search(
                MultiDict({'query': 'random',
                           'searchtype': 'all',
                           'abstracts': 'show'}), None)
            hit = next(
                (hit for hit in data['results'] if '9603088' in hit['id']),
                'not found')
            self.assertTrue(hit['truncated']['abstract'],
                            'Should be flagged truncated due to front trunc')

            data, rs, _ = simple.search(
                MultiDict({'query': 'random',
                           'searchtype': 'all',
                           'abstracts': 'show'}), None)
            hit = next(
                (hit for hit in data['results'] if '9603088' in hit['id']),
                'not found')
            self.assertTrue(hit['truncated']['abstract'],
                            'Should be flagged truncated due to front trunc')

    def test_trunc(self):
        """Checks that all results have resonable truncated flags."""
        with self.app.app_context():
            data, rs, _ = simple.search(
                MultiDict({'query': 'random',
                           'searchtype': 'all',
                           'abstracts': 'show'}), None)
            for res in data['results']:
                has_preview = 'preview' in res and 'abstract' in res['preview']
                is_trunc = 'truncated' in res and 'abstract' in res[
                    'truncated'] and res['truncated']['abstract']
                if is_trunc and not has_preview:
                    self.fail("Missing preview when flaged as truncated")

    def test_arxivng_3510(self):
        """search display not escaping special characters"""
        client = self.app.test_client()
        rv = client.get('/?query=carella')
        self.assertNotIn('<s ', rv.data.decode('utf-8'),
                         '"<s " in tex must be escaped to avoid strikethrough')

