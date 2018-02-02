""" Utility functions for arxiv.search """
import re

__all__ = ['parse_arxiv_id']

CATEGORIES = [
    "acc-phys", "adap-org", "alg-geom", "ao-sci", "astro-ph", "atom-ph",
    "bayes-an", "chao-dyn", "chem-ph", "cmp-lg", "comp-gas", "cond-mat", "cs",
    "dg-ga", "funct-an", "gr-qc", "hep-ex", "hep-lat", "hep-ph", "hep-th",
    "math", "math-ph", "mtrl-th", "nlin", "nucl-ex", "nucl-th", "patt-sol",
    "physics", "plasm-ph", "q-alg", "q-bio", "quant-ph", "solv-int",
    "supr-con", "eess", "econ"
]

ARXIV_REGEX = ("^(ar[xX]iv:)?((?:(?:(?:%s)(?:[.][A-Z]{2})?/[0-9]{2}(?:0[1-9]|1[0-2])"
         "\\d{3}(?:[vV]\\d+)?))|(?:(?:[0-9]{2}(?:0[1-9]|1[0-2])[.]"

def parse_arxiv_id(value: str) -> str:
    """
    Parse arxiv id from string. 
    
    Raises `ValidationError` if no arXiv ID.
    """
    m = re.search(ARXIV_REGEX, value)
    if not m:
        raise ValueError('Not a valid arXiv ID')
    return m.group(2)

