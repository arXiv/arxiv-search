"""Tests for :mod:`search.services.tex`."""

import unittest
from search.services import tex

dispaly_txt=r'''where $\alpha \neq 0, $ and either both $\alpha, t $ are real, or both are
pure imaginary numbers. For even $n$ we prove: if $t, n $ are fixed, then, for
$ \alpha \to 0, $
  $$ \gamma_n = | \frac{8\alpha^n}{2^n [(n-1)!]^2} \prod_{k=1}^{n/2}  (t^2 -
(2k-1)^2)  |  $ (1 + O(\alpha)), $$
 and if $ \alpha, t $ are fixed, then, for $ n \to \infty, $
  $$ \gamma_n = \frac{8 |\alpha/2|^n}{[2 \cdot 4 ... (n-2)]^2}  | \cos
(\frac{\pi}{2} t) |  [ 1 + O  (\frac{\log n}{n})  ]. $$
  Similar formulae (see Theorems \ref{thm2} and \ref{thm4}) hold for odd $n.$'''

    
class TestTeX(unittest.TestCase):
    """test."""

            
    def test_inline(self):
        """Test math postitions"""
        pos = tex.math_positions('some stuff $crazy tex!$ other stuff $more tex$')
        self.assertEqual( [(11,23),(36,46)] , pos )

        pos = tex.math_positions('$crazy tex!$ other stuff $more tex$')
        self.assertEqual( [(0,12),(25,35)] , pos )

        pos = tex.math_positions('$crazy tex!$')
        self.assertEqual( [(0,12)] , pos )
        
    def test_display(self):
        """Test math postitions"""
        txt = dispaly_txt
        pos = tex.math_positions(txt)
        for start,end in pos:
            self.assertEqual('$' , txt[start], "should start with $ or $$ delimiter")
            self.assertEqual('$',  txt[end-1], "should end with $ or $$ delimiter")

    def test_inline_pren(self):
        txt = 'critical density \\(p_{c}(Ng)\\) which is in the intermediate'
        pos = tex.math_positions(txt)
        self.assertEqual([(17,30)], pos)

    def test_display2(self):
        txt = "critical density \\[p_{c}\n(Ng)[something] or other \\] which is in the intermeidiate"
        pos = tex.math_positions(txt)
        self.assertEqual([(17,52)], pos)

        txt = "\\[p_{c}\n(Ng)[something] or other \\] which is in the intermediate"
        pos = tex.math_positions(txt)
        self.assertEqual([(0,35)], pos)

        txt = "critical density \\[p_{c}\n(Ng)[something] or other \\]"
        pos = tex.math_positions(txt)
        self.assertEqual([(17,52)], pos)


    def test_split(self):
        txt = 'some stuff $crazy tex!$ other stuff $more tex$ more at the end'
        txtf = tex.split_for_maths(tex.math_positions(txt), txt)
        self.assertEqual(  ''.join(txtf) , txt, )

        self.assertEqual( len([ True for chunk in txtf if tex.isMath(chunk)] ), 2 )
        
        txtf = tex.split_for_maths( tex.math_positions(dispaly_txt),dispaly_txt)
        self.assertEqual(''.join(txtf), dispaly_txt)
        self.assertTrue( any( [ tex.isMath(chunk) for chunk in txtf] ) )
