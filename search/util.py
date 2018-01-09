""" Utility functions for arxiv.search """
import re

__all__ = ['parse_arxiv_id']

ARXIV_REGEX = ("((?:(?:(?:%s)(?:[.][A-Z]{2})?/[0-9]{2}(?:0[1-9]|1[0-2])"
         "\\d{3}(?:[vV]\\d+)?))|(?:(?:[0-9]{2}(?:0[1-9]|1[0-2])[.]"
         "\\d{4,5}(?:[vV]\\d+)?)))" % '|'.join(CATEGORIES))

def parse_arxiv_id(value: str) -> str:
    """
    Parse arxiv id from string. 
    
    Raises `ValidationError` if no arXiv ID.
    """
    m = re.match(ARXIV_REGEX, value)
    if not m:
        raise ValidationError('Not a valid arXiv ID')
    return m.group(1)

