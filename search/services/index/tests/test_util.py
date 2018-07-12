"""Tests for :mod:`search.services.index.util`."""

from unittest import TestCase

from search.services.index import util


class TestMatchDatePartial(TestCase):
    """Tests for :func:`.index.util.match_date_partial`."""

    def test_date_partial_only(self):
        """Term includes only a four-digit date partial."""
        term, rmd = util.match_date('1902')
        ym = util.match_date_partial(term)
        self.assertEqual(ym, '2019-02')
        self.assertEqual(rmd, '', "Should have no remainder")

    def test_in_word(self):
        """A false positive in a word."""
        with self.assertRaises(ValueError):
            term, rmd = util.match_date('notasearch1902foradatepartial')

    def test_near_words(self):
        """Term includes date partial plus other terms."""
        term, rmd = util.match_date('foo 1902 bar')
        ym = util.match_date_partial(term)
        self.assertEqual(ym, '2019-02')
        self.assertEqual(rmd, "foo bar", "Should have remainder")

    def test_out_of_range(self):
        """Term looks like a date partial, but is not a valid date."""
        term, rmd = util.match_date('0699')
        self.assertIsNone(util.match_date_partial(term))

    def test_last_millenium(self):
        """Term is for a pre-2000 paper."""
        term, rmd = util.match_date('old paper 9505')
        ym = util.match_date_partial(term)
        self.assertEqual(ym, '1995-05')
        self.assertEqual(rmd, 'old paper', 'Should have a remainder')
