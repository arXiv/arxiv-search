"""Tests for :mod:`search.services.index`."""

from unittest import TestCase
from search.services.index import highlighting
from jinja2 import Markup
from search.domain import Document

class TestResultsHighlightAbstract(TestCase):
    """Given a highlighted abstract, generate a safe preview."""

    def setUp(self):
        """Set a sample abstract for use in test cases."""
        self.value = (
            "A search for the standard model (SM) Higgs boson ($\\mathrm{H}"
            "$) decaying to $\\mathrm{b}\\overline{\\mathrm{b}}$ when produced"
            " in association with an electroweak vector boson is reported for"
            " the following processes: <em>$\\mathrm{b}\\overline{\\mathrm{b}}"
            "(\\nu\\nu)\\mathrm{H}$</em>, $\\mathrm{W}(\\mu\\nu)\\mathrm{H}$,"
            " $\\mathrm{W}(\\mathrm{e} \\nu)\\mathrm{H}$,"
            " $\\mathrm{Z}(\\mu\\mu)\\mathrm{H}$, and"
            " $\\mathrm{Z}(\\mathrm{e}\\mathrm{e})\\mathrm{H}$."
        )
        self.start_tag = "<em>"
        self.end_tag = "</em>"

    def test_preview(self):
        """Generate a preview that is smaller than/equal to fragment size."""
        preview,trunc = highlighting.preview(
            self.value,
            fragment_size=350,
            start_tag=self.start_tag,
            end_tag=self.end_tag,
        )
        self.assertGreaterEqual(338, len(preview))
        self.assertTrue( trunc )


    def test_preview_with_close_highlights(self):
        """Two highlights in the abstract are close together."""
        value = (
            "We investigate self-averaging properties in the transport of"
            ' particles through <span class="has-text-success'
            ' has-text-weight-bold mathjax">random</span> media. We show'
            " rigorously that in the subdiffusive anomalous regime transport"
            " coefficients are not self--averaging quantities. These"
            " quantities are exactly calculated in the case of directed"
            ' <span class="has-text-success has-text-weight-bold mathjax">'
            "random</span> walks. In the case of general symmetric <span"
            ' class="has-text-success has-text-weight-bold mathjax">random'
            "</span> walks a perturbative analysis around the Effective Medium"
            " Approximation (EMA) is performed."
        )
        start_tag = (
            '<span class="has-text-success has-text-weight-bold mathjax">'
        )
        end_tag = "</span>"
        preview,trunc = highlighting.preview(value, start_tag=start_tag, end_tag=end_tag)
        self.assertGreater(len(preview), 100)
        self.assertTrue(trunc)


class TestResultsEndSafely(TestCase):
    """Given a highlighted abstract, find a safe end index for the preview."""

    def setUp(self):
        """Set a sample abstract for use in test cases."""
        self.value = (
            "A search for the standard model (SM) Higgs boson ($\\mathrm{H}"
            "$) decaying to $\\mathrm{b}\\overline{\\mathrm{b}}$ when produced"
            " in association with an electroweak vector boson is reported for"
            " the following processes: <em>$\\mathrm{b}\\overline{\\mathrm{b}}"
            "(\\nu\\nu)\\mathrm{H}$</em>, $\\mathrm{W}(\\mu\\nu)\\mathrm{H}$,"
            " $\\mathrm{W}(\\mathrm{e} \\nu)\\mathrm{H}$,"
            " $\\mathrm{Z}(\\mu\\mu)\\mathrm{H}$, and"
            " $\\mathrm{Z}(\\mathrm{e}\\mathrm{e})\\mathrm{H}$."
        )
        self.start_tag = "<em>"
        self.end_tag = "</em>"

    def test_end_safely_from_start(self):
        """No TeXisms/HTML are found within the desired fragment size."""
        end = highlighting._end_safely(
            self.value, 45, start_tag=self.start_tag, end_tag=self.end_tag
        )
        self.assertEqual(end, 45, "Should end at the desired fragment length.")

    def test_end_safely_before_texism(self):
        """End before TeXism when desired fragment size would truncate."""
        end = highlighting._end_safely(
            self.value, 55, start_tag=self.start_tag, end_tag=self.end_tag
        )
        # print(self.value[:end])
        self.assertEqual(end, 50, "Should end before the start of the TeXism.")

    def test_end_safely_before_html(self):
        """End before HTML when desired fragment size would truncate."""
        end = highlighting._end_safely(
            self.value, 215, start_tag=self.start_tag, end_tag=self.end_tag
        )
        self.assertEqual(end, 213, "Should end before the start of the tag.")

    def test_end_safely_after_html_with_tolerance(self):
        """End before HTML when desired fragment size would truncate."""
        end = highlighting._end_safely(
            self.value, 275, start_tag=self.start_tag, end_tag=self.end_tag
        )
        self.assertEqual(end, 275, "Should end after the closing tag.")


class Collapse(TestCase):
    """Tests function that collapses unbalanced tags inside a string."""
    def collapse_hl_tags(self):
        hopen,hclose = highlighting.HIGHLIGHT_TAG_OPEN, highlighting.HIGHLIGHT_TAG_CLOSE
        self.assertEqual(0, highlighting.collapse_hl_tags(''))
        self.assertEqual(0, highlighting.collapse_hl_tags('something or other <tag> </closetag> but not important'))
        self.assertEqual(3, highlighting.collapse_hl_tags( highlighting.HIGHLIGHT_TAG_OPEN * 3))
        self.assertEqual(-3, highlighting.collapse_hl_tags( highlighting.HIGHLIGHT_TAG_CLOSE * 3))
        self.assertEqual(1, highlighting.collapse_hl_tags( hopen+hopen+hclose))
        self.assertEqual(-1, highlighting.collapse_hl_tags( hopen+ hclose+ hclose))
        self.assertEqual(0, highlighting.collapse_hl_tags( hopen+hopen+hclose+hclose))
        self.assertEqual(0, highlighting.collapse_hl_tags( hopen+ hclose+ hopen+ hclose))

        
class Texism(TestCase):
    """Tests highligh of TeX."""
    def test_highlight_whole_texism(self):
        value = 'the ' + highlighting.HIGHLIGHT_TAG_OPEN + 'subsets'+highlighting.HIGHLIGHT_TAG_CLOSE+\
            ''' of triples $\{1, e, π\}$, $\{1, e, π^{-1}\}$, and $\{1, π^r, π^s\}$, where $1\leq r<s $ are fixed integers.'''

        hlwt = highlighting._highlight_whole_texism(value)
        self.assertIn( 'are fixed integers' , hlwt, "should not chop off end")
        self.assertTrue( hlwt.startswith("the "), "should not chop off front")
        self.assertIn( 'subsets' , hlwt, "should not chop off front")

    def test_escape_nontex(self):
        tt = "this is non-tex no problem"
        self.assertEqual(tt, highlighting._escape_nontex(tt)  )


class Highlight(TestCase):
    def test_hi1(self):
        value = 'due in <span class="search-hit mathjax">large</span> part of xyz'
        hl = highlighting._highlight_whole_texism(value)
        self.assertGreater(len(hl), 0)
        self.assertIn("<span", hl)
        self.assertNotIn('&lt', hl)
